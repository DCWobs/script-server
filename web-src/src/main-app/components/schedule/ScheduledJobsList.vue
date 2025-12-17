<template>
  <div class="scheduled-jobs-list">
    <div class="scheduled-jobs-header">
      <span class="header-title">Scheduled Jobs</span>
      <button class="btn-flat btn-small refresh-btn" @click="refresh" :disabled="loading">
        <i class="material-icons">refresh</i>
      </button>
    </div>
    
    <div v-if="loading" class="loading-indicator">
      <div class="preloader-wrapper small active">
        <div class="spinner-layer spinner-primary-only">
          <div class="circle-clipper left"><div class="circle"></div></div>
          <div class="gap-patch"><div class="circle"></div></div>
          <div class="circle-clipper right"><div class="circle"></div></div>
        </div>
      </div>
    </div>
    
    <div v-else-if="filteredSchedules.length === 0" class="no-schedules">
      No scheduled jobs for this script
    </div>
    
    <div v-else class="schedules-container">
      <div v-for="schedule in filteredSchedules" :key="schedule.id" class="schedule-item">
        <div class="schedule-info">
          <div class="schedule-main">
            <span class="schedule-id">#{{ schedule.id }}</span>
            <span class="schedule-type">{{ formatScheduleType(schedule) }}</span>
          </div>
          <div class="schedule-details">
            <span class="schedule-next" v-if="schedule.next_execution">
              Next: {{ formatDate(schedule.next_execution) }}
            </span>
            <span class="schedule-next expired" v-else>
              Expired
            </span>
          </div>
          <div class="schedule-params" v-if="hasParams(schedule)">
            <span class="param" v-for="(value, key) in schedule.parameter_values" :key="key">
              {{ key }}: {{ formatParamValue(value) }}
            </span>
          </div>
        </div>
        <div class="schedule-actions">
          <button class="btn-flat btn-small" @click="editSchedule(schedule)" title="Edit">
            <i class="material-icons">edit</i>
          </button>
          <button class="btn-flat btn-small delete-btn" @click="confirmDelete(schedule)" title="Delete">
            <i class="material-icons">delete</i>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Delete confirmation modal -->
    <div ref="deleteModal" class="modal">
      <div class="modal-content">
        <h5>Delete Scheduled Job</h5>
        <p>Are you sure you want to delete scheduled job #{{ scheduleToDelete?.id }}?</p>
      </div>
      <div class="modal-footer">
        <a class="modal-close waves-effect btn-flat">Cancel</a>
        <a class="waves-effect btn-flat red-text" @click="deleteSchedule">Delete</a>
      </div>
    </div>
  </div>
</template>

<script>
import {mapState, mapActions, mapGetters} from 'vuex';
import '@/common/materializecss/imports/modals';

export default {
  name: 'ScheduledJobsList',
  
  props: {
    scriptName: {
      type: String,
      default: null
    }
  },
  
  data() {
    return {
      scheduleToDelete: null,
      deleteModalInstance: null
    };
  },
  
  computed: {
    ...mapState('schedules', ['schedules', 'loading']),
    ...mapGetters('schedules', ['getSchedulesByScript']),
    
    filteredSchedules() {
      if (this.scriptName) {
        return this.getSchedulesByScript(this.scriptName);
      }
      return this.schedules;
    }
  },
  
  mounted() {
    this.refresh();
    this.deleteModalInstance = M.Modal.init(this.$refs.deleteModal);
  },
  
  beforeDestroy() {
    if (this.deleteModalInstance) {
      this.deleteModalInstance.destroy();
    }
  },
  
  watch: {
    scriptName() {
      this.refresh();
    }
  },
  
  methods: {
    ...mapActions('schedules', ['fetchSchedules', 'deleteSchedule as deleteScheduleAction']),
    
    async refresh() {
      try {
        await this.fetchSchedules({scriptName: this.scriptName});
      } catch (e) {
        M.toast({html: 'Failed to load schedules'});
      }
    },
    
    formatScheduleType(schedule) {
      const s = schedule.schedule;
      if (!s.repeatable) {
        return 'One-time';
      }
      
      const period = s.repeat_period || 1;
      const unit = s.repeat_unit || 'days';
      
      if (period === 1) {
        const unitSingular = unit.replace(/s$/, '');
        return `Every ${unitSingular}`;
      }
      return `Every ${period} ${unit}`;
    },
    
    formatDate(isoString) {
      if (!isoString) return 'N/A';
      const date = new Date(isoString);
      return date.toLocaleString();
    },
    
    hasParams(schedule) {
      return schedule.parameter_values && Object.keys(schedule.parameter_values).length > 0;
    },
    
    formatParamValue(value) {
      if (Array.isArray(value)) {
        return value.join(', ');
      }
      if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
      }
      return String(value).substring(0, 30);
    },
    
    editSchedule(schedule) {
      this.$emit('edit', schedule);
    },
    
    confirmDelete(schedule) {
      this.scheduleToDelete = schedule;
      this.deleteModalInstance.open();
    },
    
    async deleteSchedule() {
      if (!this.scheduleToDelete) return;
      
      try {
        await this.deleteScheduleAction({jobId: this.scheduleToDelete.id});
        M.toast({html: `Deleted schedule #${this.scheduleToDelete.id}`});
        this.deleteModalInstance.close();
        this.scheduleToDelete = null;
      } catch (e) {
        M.toast({html: 'Failed to delete schedule'});
      }
    }
  }
};
</script>

<style scoped>
.scheduled-jobs-list {
  background: var(--background-color-level-4dp);
  border-radius: 4px;
  padding: 12px;
  margin-top: 12px;
}

.scheduled-jobs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--separator-color);
}

.header-title {
  font-weight: 500;
  color: var(--primary-color);
}

.refresh-btn {
  padding: 0 8px;
}

.refresh-btn i {
  font-size: 20px;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.no-schedules {
  text-align: center;
  color: var(--font-color-medium);
  padding: 16px;
  font-style: italic;
}

.schedules-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.schedule-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--background-color-level-2dp);
  border-radius: 4px;
  border-left: 3px solid var(--primary-color);
}

.schedule-info {
  flex: 1;
  min-width: 0;
}

.schedule-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.schedule-id {
  font-weight: 600;
  color: var(--primary-color);
}

.schedule-type {
  font-size: 0.9em;
  color: var(--font-color-main);
}

.schedule-details {
  font-size: 0.85em;
  color: var(--font-color-medium);
}

.schedule-next.expired {
  color: var(--error-color, #f44336);
}

.schedule-params {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.schedule-params .param {
  font-size: 0.8em;
  background: var(--background-color-level-6dp);
  padding: 2px 6px;
  border-radius: 3px;
  color: var(--font-color-medium);
}

.schedule-actions {
  display: flex;
  gap: 4px;
}

.schedule-actions .btn-flat {
  padding: 0 6px;
  min-width: 0;
  height: 28px;
  line-height: 28px;
}

.schedule-actions .btn-flat i {
  font-size: 18px;
}

.delete-btn:hover {
  color: var(--error-color, #f44336);
}

.modal {
  max-width: 400px;
}
</style>

