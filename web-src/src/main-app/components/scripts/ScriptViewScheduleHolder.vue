<template>
  <div>
    <div v-if="mobileView && showSchedulePanel" ref="scheduleModal" class="modal">
      <SchedulePanel :mobile-view="true" 
                     :editingSchedule="editingSchedule"
                     @close="closeSchedulePanel"/>
    </div>
    <SchedulePanel v-else-if="showSchedulePanel" 
                   :editingSchedule="editingSchedule"
                   @close="closeSchedulePanel"/>
    <ScheduledJobsList v-if="schedulable && !showSchedulePanel"
                       :scriptName="scriptName"
                       @edit="handleEditSchedule"/>
  </div>
</template>

<script>
import {mapState} from 'vuex';
import {isNull} from '@/common/utils/common';
import SchedulePanel from '@/main-app/components/schedule/SchedulePanel';
import ScheduledJobsList from '@/main-app/components/schedule/ScheduledJobsList';

export default {
  name: 'ScriptViewScheduleHolder',

  components: {
    SchedulePanel,
    ScheduledJobsList
  },

  props: {
    scriptConfigComponentsHeight: {
      type: Number,
      default: 0
    },
  },
  data: function () {
    return {
      mobileView: false,
      showSchedulePanel: false,
      scheduleModal: null,
      editingSchedule: null
    }
  },

  mounted: function () {
    window.addEventListener('resize', this.resizeListener);
    this.resizeListener();
  },

  beforeDestroy: function () {
    window.removeEventListener('resize', this.resizeListener);
  },

  computed: {
    ...mapState('scriptConfig', {
      scriptConfig: 'scriptConfig'
    }),
    
    schedulable() {
      return this.scriptConfig && this.scriptConfig.schedulable;
    },
    
    scriptName() {
      return this.scriptConfig ? this.scriptConfig.name : null;
    }
  },

  methods: {
    open() {
      this.editingSchedule = null;
      this.showSchedulePanel = true;
    },
    
    handleEditSchedule(schedule) {
      this.editingSchedule = schedule;
      this.showSchedulePanel = true;
    },
    
    closeSchedulePanel() {
      this.showSchedulePanel = false;
      this.editingSchedule = null;
    },

    resizeListener: function () {
      // 400 for schedule panel
      this.mobileView = (window.innerHeight - this.scriptConfigComponentsHeight - 400) < 0;
    },

    updateScheduleVisibility: function () {
      if (!this.mobileView || !this.showSchedulePanel) {
        if (!isNull(this.scheduleModal)) {
          this.scheduleModal.destroy();
          this.scheduleModal = null;
        }
      } else {
        if (isNull(this.scheduleModal)) {
          this.scheduleModal = M.Modal.init(this.$refs.scheduleModal,
              {onCloseStart: () => this.showSchedulePanel = false});
        }
        this.scheduleModal.open();
      }
    }

  },

  watch: {
    mobileView: function () {
      this.$nextTick(() => {
        this.updateScheduleVisibility()
      });
    },

    showSchedulePanel: function (newValue) {
      this.$nextTick(() => {
        this.updateScheduleVisibility()
      });

      if (!newValue) {
        this.editingSchedule = null;
        this.$emit('close');
      }
    },

    scriptConfig: function () {
      this.$nextTick(() => this.resizeListener())
      this.showSchedulePanel = false;
    },

    scriptConfigComponentsHeight: function () {
      this.$nextTick(() => this.resizeListener());
    }
  },
}

</script>

<style scoped>
.modal {
  width: fit-content;
}

.modal .schedule-panel {
  margin: 0;
}

div:not(.modal) > .schedule-panel {
  margin-left: auto;
  margin-top: 12px;
  background-color: var(--background-color-level-4dp);
}

div > .schedule-panel >>> .card-action {
  background: none;
}
</style>