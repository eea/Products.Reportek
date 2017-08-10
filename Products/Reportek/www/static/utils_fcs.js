/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.fcs = {
    load: function() {
      var self = reportek.utils.fcs;
      self.initCompaniesTable();
    },
    initCompaniesTable: function() {
      $.fn.dataTable.moment( 'DD/MM/YYYY' );
      $("#comp-table").dataTable({
        "iDisplayLength": 20,
        "sAjaxSource": "/fgases_registry/get_companies",
        "sAjaxDataProp" : "",
        "autowidth": false,
        "order": [[ 0, "desc" ]],
        "columns": [
          { "width": "5%%" },
          { "width": "25%" },
          { "width": "15%" },
          { "width": "13%" },
          { "width": "15%" },
          { "width": "12%" },
          { "width": "15%" }
        ],
        "aoColumns": [
          { "mData": "company_id" },  // for User Detail
          { "mData": "name" },
          { "mData": "domain" },
          { "mData": "users" },
          { "mData": "address.country.name" },
          { "mData": "vat" },
          { "mData": "date_created" }
        ],
        "columnDefs": [
          {
            "width": "25%",
            "targets": 1,
            "data": "name",
            "render": function (data, type, full) {
              return "<a href='/fgases_registry/organisation_details?id=" +
                      full.company_id + "'>" + data + "</a>";
            }
          },
          {
            "width": "13%",
            "targets": 3,
            "data": "users",
            "render": function (data, type, full) {
              var result = "";
              for (var i = 0; i < data.length; i++) {
                result += "<a href='/fgases_registry/organisation_details?id=" +
                          full.company_id + "'>" + data[i].username + "</a><br/>";
              }
              return result;
            }
          }
        ]
      });
    }
};

$(document).ready(function () {
  reportek.utils.fcs.load();
});
