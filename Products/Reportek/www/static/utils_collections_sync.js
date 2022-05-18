/*global $*/
/*global document*/
/*global window*/
/*global alert*/
/*jslint browser:true */
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.collections_sync = {
  load: function() {
    var self = reportek.utils.collections_sync;
    self.bind_tabs();
    self.init_table();
    self.bind_age_controls();
  },

  bind_tabs: function() {
    var self = reportek.utils.collections_sync;
    $(".ajaxtabsmenu a").on("click", function() {
      self.update_table_values();
    });
  },

  bind_age_controls: function() {
    var self = reportek.utils.collections_sync;
    function isInt(n) {
      if(typeof n==='number' && (n%1)===0) {
        return true;
      }
      return false;
    }
    var age = 30;
    $("#age").on('keyup', function (e) {
      if (e.keyCode == 13) {
        age = parseInt($(this).val(), 10);
        if (isInt(age) && age > 0) {
          self.update_table_values();
        } else {
          alert("Please enter the number of days!");
          return;
        }
      }
    });
    $("input[name='update']").on("click", function() {
      age = parseInt($("#age").val(), 10);
      if (isInt(age) && age > 0) {
        self.update_table_values();
        $("#age_info").text($("#age").val());
      } else {
          alert("Please enter the number of days!");
          return;
      }
    });
  },

  init_table: function() {
    var self = reportek.utils.collections_sync;
    $("#f_colls").DataTable({
      "iDisplayLength": 50,
      "bProcessing": true,
      "ajax": {
        "url": "get_collections_sync",
        "type": "GET",
        "dataSrc": ""
      },
      "bAutoWidth": false,
      "order": [[ 1, "asc" ]],
      "columnDefs": [
        {
          "targets": 0,
          "render": function (data, type, full, meta) {
            return '<input type="checkbox" name="collections:list" class="toggledCB" value="' + full.path + '">';
          }
        },
        {
          "targets": 1,
          "render": function (data, type, full, meta) {
            return '<a href="' + full.path + '">' + full.path + '</a>';
          }
        },
        {
          "targets": 2,
          "render": function (data, type, full, meta) {
            return full.modified;
          }
        },
        {
          "targets": 3,
          "render": function (data, type, full, meta) {
            return full.ack;
          }
        }
      ]
    });
  },
  update_table_values: function() {
    var self = reportek.utils.collections_sync;
    var table = $("#s_envs").DataTable();
    table.ajax.url(self.get_data_url()).load();
  }
};

$(document).ready(function () {
  reportek.utils.collections_sync.load();
});
