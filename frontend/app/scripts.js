const base = `${window.location.origin}/api/v1`;

const app = new Vue({
  el: '#app',
  data: {
    query: {root_id: '', historical: false, filtered: true},
    filters: {

    },
    response: [],
    headers: [],
    csv: '',
    status: 'Submit',
    loading: false
  },
  computed: {
    isReady: function() {
      return this.query.root_id.length &&
          !isNaN(parseInt(this.query.root_id)) && !this.loading;
    }
  },
  methods: {
    apiRequest: async function() {
      // Disable button, activate spinner
      this.loading = true;
      this.status = 'Loading...';

      const request = new URL(`${base}/get/`);
      request.searchParams.set('query', this.query.root_id);
      request.searchParams.set('root_ids', this.query.historical);
      request.searchParams.set('filtered', this.query.filtered);

      try {
        const response = await fetch(request);
        await this.processData(await response.json());
        this.status = 'Submit';
        this.loading = false;
      } catch (e) {
        alert(`Root ID: ${this.query.root_id} is invalid.`);
        this.loading = false;
        this.status = 'Submit';
        throw e;
      }
    },
    processData: function(response) {
      rawData = JSON.parse(response.json);
      if (rawData.length) {
        this.headers = Object.keys(rawData[0]);
        this.response = rawData;
      }
      this.csv = response.csv.replace(/\[|\]/g, '');
    },
    exportCSV: function() {
      const filename = 'edits.csv';
      const blob = new Blob([this.csv], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    }
  }
});