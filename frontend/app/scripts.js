const base = `${window.location.origin}/api/v1`;

const app = new Vue({
  el: '#app',
  data: {
    query: {root_id: '', historical: false, filtered: true},
    filters: {

    },
    response: [],
    headers: [],
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

      /*const request =
          new URL(`${base}/get/${this.query.root_id}/tabular_change_log`);*/
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
      const data = {};
      const keys = Object.keys(response);
      this.headers = ['', ...keys]

          const head = response[keys[0]];
      Object.keys(head).forEach(v => {
        data[v] = {};
        keys.forEach(e => {
          data[v][e] = response[e][v];
        });
      });
      this.response = Object.entries(data);
    },
    exportCSV: function() {
      const filename = 'edits.csv';
      const header = [
        '', 'operation_id', 'timestamp', 'user_id', 'is_merge', 'user_name'
      ].join(',');
      const arrayForm = this.response.map(entry => {
        return [entry[0], Object.values(entry[1])].join(',');
      });
      const csvString = [header, ...arrayForm].join('\n');
      const blob = new Blob([csvString], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    }
  }
});