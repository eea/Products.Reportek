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

reportek.utils.stuck_envelopes = {
  load: function() {
    var self = reportek.utils.stuck_envelopes;
    self.bind_tabs();
    self.init_table();
    self.bind_age_controls();
  },

  bind_tabs: function() {
    var self = reportek.utils.stuck_envelopes;
    $(".ajaxtabsmenu a").on("click", function() {
      self.update_table_values();
    });
  },

  bind_age_controls: function() {
    var self = reportek.utils.stuck_envelopes;
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

  get_data_url: function() {
    var key = $(".tabbed-content:visible").attr("id");
    var age = $("#age").val();
    var urls = {
      "": "get_stuck_envelopes",
      "lr-aqa": "get_lr_aqa_envelopes?age=" + age,
      "stuck-inactive": "get_stuck_envelopes"
    };
    return urls[key];
  },

  init_table: function() {
    var self = reportek.utils.stuck_envelopes;
    $("#s_envs").DataTable({
      "iDisplayLength": 50,
      "bProcessing": true,
      "ajax": {
        "url": self.get_data_url(),
        "type": "GET",
        "dataSrc": ""
      },
      "bAutoWidth": false,
      "order": [[ 1, "asc" ]],
      "columnDefs": [
        {
          "targets": 0,
          "render": function (data, type, full, meta) {
            return '<a href="' + full.env.url + '">' + full.env.path + '</a>';
          }
        },
        {
          "targets": 1,
          "render": function (data, type, full, meta) {
            return '<a href="' + full.process.url + '">' + full.process.title + '</a>';
          }
        },
        {
          "targets": 2,
          "render": function (data, type, full, meta) {
            return '<a href="' + full.activity.url + '">' + full.activity.title + '</a>';
          }
        },
        {
          "targets": 3,
          "data": "s_date"
        }
      ]
    });
  },
  update_table_values: function() {
    var self = reportek.utils.stuck_envelopes;
    var table = $("#s_envs").DataTable();
    table.ajax.url(self.get_data_url()).load();
  }
};

$(document).ready(function () {
  reportek.utils.stuck_envelopes.load();
});
