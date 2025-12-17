import {axiosInstance} from '@/common/utils/axios_utils';

export default {
    state: {
        schedules: [],
        loading: false,
        error: null
    },
    namespaced: true,
    
    mutations: {
        setSchedules(state, schedules) {
            state.schedules = schedules;
        },
        setLoading(state, loading) {
            state.loading = loading;
        },
        setError(state, error) {
            state.error = error;
        },
        removeSchedule(state, jobId) {
            state.schedules = state.schedules.filter(s => s.id !== jobId);
        }
    },
    
    actions: {
        async fetchSchedules({commit}, {scriptName} = {}) {
            commit('setLoading', true);
            commit('setError', null);
            
            try {
                const params = scriptName ? `?script=${encodeURIComponent(scriptName)}` : '';
                const response = await axiosInstance.get(`schedules${params}`);
                commit('setSchedules', response.data);
            } catch (e) {
                commit('setError', e.response?.data || e.message);
                throw e;
            } finally {
                commit('setLoading', false);
            }
        },
        
        async deleteSchedule({commit}, {jobId}) {
            try {
                await axiosInstance.delete(`schedules/${jobId}/delete`);
                commit('removeSchedule', jobId);
                return true;
            } catch (e) {
                throw e;
            }
        },
        
        async updateSchedule({dispatch}, {jobId, schedule}) {
            try {
                await axiosInstance.put(`schedules/${jobId}/update`, {schedule});
                // Refresh the list after update
                await dispatch('fetchSchedules');
                return true;
            } catch (e) {
                throw e;
            }
        }
    },
    
    getters: {
        getSchedulesByScript: (state) => (scriptName) => {
            return state.schedules.filter(s => s.script_name === scriptName);
        }
    }
}

