/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.fcs = {
    base_url: '/fgases_registry',
    companies: '/get_companies',
    company_details: '/organisation_details',
    domain: 'FGAS',

    load: function() {
      var self = reportek.utils.fcs;
      self.domain = $("#domain").val();
      self.update_domain_param();
      self.companies_url = self.base_url + self.companies;
      self.company_details_url = self.base_url + self.company_details;
      self.initCompaniesTable();
      self.bind_obl_select();
    },
    update_domain_param: function() {
      var self = reportek.utils.fcs;
      var anchors = $(".export");
      for (var i=0; i<anchors.length; i++) {
        var href = $(anchors[i]).attr("href");
        $(anchors[i]).attr("href", href.split('?')[0] + '?domain=' + self.domain);
      }
    },
    get_companies_url: function() {
      var self = reportek.utils.fcs;
      var params = { domain: self.domain };
      return self.companies_url + '?' + $.param( params );
    },
    bind_obl_select: function() {
      var self = reportek.utils.fcs;
      $("#domain").on("change", {self:this}, function(evt){
        evt.preventDefault();
        self = evt.data.self;
        self.domain = $(this).val();
        self.tbl.ajax.url(self.get_companies_url());
        self.tbl.ajax.reload();
        $("#obligation").text(self.domain);
        self.update_domain_param();
      });
    },
    initCompaniesTable: function() {
      var self = reportek.utils.fcs;
      $.fn.dataTable.moment( 'DD/MM/YYYY' );
      self.tbl = $("#comp-table").DataTable({
        "iDisplayLength": 20,
        "ajax": {
          "url": self.get_companies_url(),
          "contentType": "application/json",
          "type": "GET",
          "dataSrc":"",
          "data": function () {

          }
        },
        "autowidth": false,
        "order": [[ 0, "desc" ]],
        "columns": [
          { "width": "5%%" },
          { "width": "25%" },
          { "width": "13%" },
          { "width": "15%" },
          { "width": "12%" },
          { "width": "15%" }
        ],
        "aoColumns": [
          { "mData": "company_id" },  // for User Detail
          { "mData": "name" },
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
              return "<a href='/fgases_registry/organisation_details?domain=" + self.domain + "&id=" +
                      full.company_id + "'>" + data + "</a>";
            }
          },
          {
            "width": "13%",
            "targets": 2,
            "data": "users",
            "render": function (data, type, full) {
              var result = "";
              for (var i = 0; i < data.length; i++) {
                result += "<a href='/fgases_registry/organisation_details?domain=" + self.domain + "&id=" +
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
