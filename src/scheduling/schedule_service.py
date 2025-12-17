import json
import logging
import os

from auth.user import User
from config.config_service import ConfigService
from execution.execution_service import ExecutionService
from execution.id_generator import IdGenerator
from scheduling import scheduling_job
from scheduling.schedule_config import read_schedule_config, InvalidScheduleException
from scheduling.scheduler import Scheduler
from scheduling.scheduling_job import SchedulingJob
from utils import file_utils, date_utils, custom_json

SCRIPT_NAME_KEY = 'script_name'
USER_KEY = 'user'
PARAM_VALUES_KEY = 'parameter_values'

JOB_SCHEDULE_KEY = 'schedule'

LOGGER = logging.getLogger('script_server.scheduling.schedule_service')


def restore_jobs(schedules_folder):
    files = [file for file in os.listdir(schedules_folder) if file.endswith('.json')]
    files.sort()

    job_path_dict = {}
    ids = []  # list of ALL ids, including broken configs

    for file in files:
        try:
            job_path = os.path.join(schedules_folder, file)
            content = file_utils.read_file(job_path)
            job_json = custom_json.loads(content)
            ids.append(job_json['id'])

            job = scheduling_job.from_dict(job_json)

            job_path_dict[job_path] = job
        except:
            LOGGER.exception('Failed to parse schedule file: ' + file)

    return job_path_dict, ids


class ScheduleService:

    def __init__(self,
                 config_service: ConfigService,
                 execution_service: ExecutionService,
                 conf_folder):
        self._schedules_folder = os.path.join(conf_folder, 'schedules')
        file_utils.prepare_folder(self._schedules_folder)

        self._config_service = config_service
        self._execution_service = execution_service

        (jobs, ids) = restore_jobs(self._schedules_folder)
        self._id_generator = IdGenerator(ids)

        self.scheduler = Scheduler()

        for job_path, job in jobs.items():
            self.schedule_job(job, job_path)

    def create_job(self, script_name, parameter_values, incoming_schedule_config, user: User):
        if user is None:
            raise InvalidUserException('User id is missing')

        config_model = self._config_service.load_config_model(script_name, user, parameter_values)
        self.validate_script_config(config_model)

        schedule_config = read_schedule_config(incoming_schedule_config)

        if not schedule_config.repeatable and date_utils.is_past(schedule_config.start_datetime):
            raise InvalidScheduleException('Start date should be in the future')

        if schedule_config.end_option == 'end_datetime':
            if schedule_config.start_datetime > schedule_config.end_arg:
                raise InvalidScheduleException('End date should be after start date')

        if schedule_config.end_option == 'max_executions' and schedule_config.end_arg <= 0:
            raise InvalidScheduleException('Count should be greater than 0!')

        id = self._id_generator.next_id()

        normalized_values = {}
        for parameter_name, value_wrapper in config_model.parameter_values.items():
            if value_wrapper.user_value is not None:
                normalized_values[parameter_name] = value_wrapper.user_value

        job = SchedulingJob(id, user, schedule_config, script_name, normalized_values)

        job_path = self.save_job(job)

        self.schedule_job(job, job_path)

        return id

    @staticmethod
    def validate_script_config(config_model):
        if not config_model.schedulable:
            raise UnavailableScriptException(config_model.name + ' is not schedulable')

        for parameter in config_model.parameters:
            if parameter.secure:
                raise UnavailableScriptException(
                    'Script contains secure parameters (' + parameter.str_name() + '), this is not supported')

    def schedule_job(self, job: SchedulingJob, job_path):
        schedule = job.schedule

        if not schedule.repeatable and date_utils.is_past(schedule.start_datetime):
            return
        
        if schedule.end_option == 'max_executions' and schedule.end_arg <= schedule.executions_count:
            return                
        
        next_datetime = schedule.get_next_time()

        if schedule.end_option == 'end_datetime':
            if next_datetime > schedule.end_arg:
                return
        
        LOGGER.info(
            'Scheduling ' + job.get_log_name() + ' at ' + next_datetime.astimezone(tz=None).strftime('%H:%M, %d %B %Y'))

        self.scheduler.schedule(next_datetime, self._execute_job, (job, job_path))

    def _execute_job(self, job: SchedulingJob, job_path):
        LOGGER.info('Executing ' + job.get_log_name())

        if not os.path.exists(job_path):
            LOGGER.info(job.get_log_name() + ' was removed, skipping execution')
            return

        script_name = job.script_name
        parameter_values = job.parameter_values
        user = job.user

        try:
            config = self._config_service.load_config_model(script_name, user, parameter_values)
            self.validate_script_config(config)

            execution_id = self._execution_service.start_script(config, user)
            LOGGER.info('Started script #' + str(execution_id) + ' for ' + job.get_log_name())

            if config.scheduling_auto_cleanup:
                def cleanup():
                    self._execution_service.cleanup_execution(execution_id, user)

                self._execution_service.add_finish_listener(cleanup, execution_id)

            if job.schedule.repeatable:
                job.schedule.executions_count += 1

                self.save_job(job)

        except:
            LOGGER.exception('Failed to execute ' + job.get_log_name())

        self.schedule_job(job, job_path)

    def save_job(self, job: SchedulingJob):
        user = job.user
        script_name = job.script_name

        filename = file_utils.to_filename('%s_%s_%s.json' % (script_name, user.get_audit_name(), job.id))
        path = os.path.join(self._schedules_folder, filename)
        file_utils.write_file(
            path,
            json.dumps(job.as_serializable_dict(), indent=2))

        return path

    def list_jobs(self, user: User, script_name: str = None) -> list:
        """List all scheduled jobs, optionally filtered by script name."""
        jobs = []
        files = [f for f in os.listdir(self._schedules_folder) if f.endswith('.json')]
        
        for file in files:
            try:
                job_path = os.path.join(self._schedules_folder, file)
                content = file_utils.read_file(job_path)
                job_json = custom_json.loads(content)
                job = scheduling_job.from_dict(job_json)
                
                # Filter by script name if provided
                if script_name and job.script_name != script_name:
                    continue
                
                # Get next execution time
                next_time = None
                if job.schedule.repeatable or not date_utils.is_past(job.schedule.start_datetime):
                    next_time = job.schedule.get_next_time()
                
                jobs.append({
                    'id': job.id,
                    'script_name': job.script_name,
                    'user': job.user.get_audit_name(),
                    'schedule': job.schedule.as_serializable_dict(),
                    'parameter_values': job.parameter_values,
                    'next_execution': next_time.isoformat() if next_time else None
                })
            except Exception:
                LOGGER.exception('Failed to read schedule file: ' + file)
        
        return jobs

    def get_job(self, job_id: str) -> dict:
        """Get a specific job by ID."""
        files = [f for f in os.listdir(self._schedules_folder) if f.endswith('.json')]
        
        for file in files:
            job_path = os.path.join(self._schedules_folder, file)
            content = file_utils.read_file(job_path)
            job_json = custom_json.loads(content)
            
            if str(job_json.get('id')) == str(job_id):
                job = scheduling_job.from_dict(job_json)
                next_time = None
                if job.schedule.repeatable or not date_utils.is_past(job.schedule.start_datetime):
                    next_time = job.schedule.get_next_time()
                
                return {
                    'id': job.id,
                    'script_name': job.script_name,
                    'user': job.user.get_audit_name(),
                    'schedule': job.schedule.as_serializable_dict(),
                    'parameter_values': job.parameter_values,
                    'next_execution': next_time.isoformat() if next_time else None
                }
        
        return None

    def delete_job(self, job_id: str, user: User) -> bool:
        """Delete a scheduled job by ID."""
        files = [f for f in os.listdir(self._schedules_folder) if f.endswith('.json')]
        
        for file in files:
            job_path = os.path.join(self._schedules_folder, file)
            content = file_utils.read_file(job_path)
            job_json = custom_json.loads(content)
            
            if str(job_json.get('id')) == str(job_id):
                os.remove(job_path)
                LOGGER.info(f'Deleted scheduled job {job_id} by user {user.get_audit_name()}')
                return True
        
        return False

    def update_job(self, job_id: str, incoming_schedule_config: dict, user: User) -> bool:
        """Update an existing job's schedule configuration."""
        files = [f for f in os.listdir(self._schedules_folder) if f.endswith('.json')]
        
        for file in files:
            job_path = os.path.join(self._schedules_folder, file)
            content = file_utils.read_file(job_path)
            job_json = custom_json.loads(content)
            
            if str(job_json.get('id')) == str(job_id):
                job = scheduling_job.from_dict(job_json)
                
                # Parse and validate new schedule config
                new_schedule = read_schedule_config(incoming_schedule_config)
                
                if new_schedule.end_option == 'end_datetime':
                    if new_schedule.start_datetime > new_schedule.end_arg:
                        raise InvalidScheduleException('End date should be after start date')
                
                if new_schedule.end_option == 'max_executions' and new_schedule.end_arg <= 0:
                    raise InvalidScheduleException('Count should be greater than 0!')
                
                # Preserve execution count for repeatable schedules
                new_schedule.executions_count = job.schedule.executions_count
                
                # Update the job
                job.schedule = new_schedule
                self.save_job(job)
                
                # Reschedule the job
                self.schedule_job(job, job_path)
                
                LOGGER.info(f'Updated scheduled job {job_id} by user {user.get_audit_name()}')
                return True
        
        return False

    def stop(self):
        self.scheduler.stop()


class InvalidUserException(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)


class UnavailableScriptException(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)
