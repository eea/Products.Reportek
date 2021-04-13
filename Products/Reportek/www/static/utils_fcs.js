/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.fcs = {
    base_url: '/european_registry',
    endpoints: {'get_companies': '/get_companies',
                'get_candidates': '/get_candidates',
                'organisation_details': '/organisation_details',
                'organisation_verification': '/organisation_verification',
                'get_stocks': '/get_stocks',
                'get_matching_log': '/get_matching_log',
                'get_datasync_log': '/get_datasync_log'},
    domain: 'FGAS',

    load: function() {
      var self = reportek.utils.fcs;
      self.domain = $("#domain").val();
      self.update_domain_param();
      self.companies_url = self.base_url + self.endpoints['companies'];
      self.init_companies();
      self.init_matched_companies();
      self.init_approval_log();
      self.init_sync_log();
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
    get_endpoint_url: function(endpoint) {
      var self = reportek.utils.fcs;
      var params = {};
        params = { domain: self.domain };
        return self.base_url + self.endpoints[endpoint] + '?' + $.param( params );

    },
    handle_domain_change: function() {
      // Hide ODS ID column for FGAS companies
      var self = reportek.utils.fcs;
      if (self.domain === 'FGAS') {
        $(".old-id").addClass("hidden-content");
      } else {
        $(".old-id").removeClass("hidden-content");
      }
    },
    bind_obl_select: function() {
      var self = reportek.utils.fcs;
      $("#domain").on("change", {self:this}, function(evt){
        self.tbl.clear().draw();
        evt.preventDefault();
        self = evt.data.self;
        self.domain = $(this).val();
        var endpoint = self.tbl_endpoint.split('/')[self.tbl_endpoint.split('/').length-1].split('?')[0];
        self.tbl.ajax.url(self.get_endpoint_url(endpoint)).load();
        self.update_domain_param();
        self.handle_domain_change();
      });
    },
    init_companies: function() {
      var self = reportek.utils.fcs;
      $.fn.dataTable.moment( 'DD/MM/YYYY' );
      if ($("#comp-table").length){
        self.tbl_endpoint = self.get_endpoint_url('get_companies');
        self.tbl = $("#comp-table").DataTable({
          "iDisplayLength": 20,
          "language": {
              processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
          },
          "ajax": {
            "url": self.tbl_endpoint,
            "contentType": "application/json",
            "type": "GET",
            "dataSrc":"",
          },
          "drawCallback": function( settings ) {
            self.handle_domain_change();
          },
          "processing": true,
          "autowidth": false,
          "order": [[ 0, "desc" ]],
          "columns": [
            { "width": "5%" },
            { "width": "5%" },
            { "width": "20%" },
            { "width": "5%" },
            { "width": "13%" },
            { "width": "15%" },
            { "width": "12%" },
            { "width": "15%" }
          ],
          "aoColumns": [
            { "mData": "company_id" },  // for User Detail
            { "mData": "oldcompany_account" },
            { "mData": "name" },
            { "mData": "status" },
            { "mData": "users" },
            { "mData": "address.country.name" },
            { "mData": "vat" },
            { "mData": "date_created" }
          ],
          "columnDefs": [
            {
            "targets": 1,
            "className": "old-id"
            },
            {
              "width": "25%",
              "targets": 2,
              "data": "name",
              "render": function (data, type, full) {
                return "<a href='" + self.get_endpoint_url('organisation_details') + "&id=" +
                        full.company_id + "'>" + data + "</a>";
              }
            },
            {
              "width": "13%",
              "targets": 4,
              "data": "users",
              "render": function (data, type, full) {
                var result = "";
                for (var i = 0; i < data.length; i++) {
                  result += "<a href='" + self.get_endpoint_url('organisation_details') + "&id=" +
                            full.company_id + "'>" + data[i].username + "</a><br/>";
                }
                return result;
              }
            }
          ]
        });
      }

      if ($("#stocks-table").length){
        self.tbl_endpoint = self.get_endpoint_url('get_stocks');
        self.tbl = $("#stocks-table").DataTable({
          "iDisplayLength": 20,
          "language": {
              processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
          },
          "ajax": {
            "url": self.tbl_endpoint,
            "contentType": "application/json",
            "type": "GET",
            "dataSrc":"",
          },
          "drawCallback": function( settings ) {
            self.handle_domain_change();
          },
          "processing": true,
          "autoWidth": false,
          "order": [[ 0, "desc" ]],
          "columns": [
            { "width": "25px" },
            { "width": "25px" },
            { "width": "450px" },
            { "width": "20px" },
            { "width": "20px" },
            { "width": "20px" },
            { "width": "20px" },
            { "width": "20px" }
          ],
          "aoColumns": [
            { "mData": "year" },
            { "mData": "company_id"},
            { "mData": "type" },
            { "mData": "substance_name_form" },
            { "mData": "is_virgin" },
            { "mData": "code" },
            { "mData": "company_name" },
            { "mData": "result" }
          ],
        });
      }
      if ($("#stocks-company-table").length){
        self.tbl_endpoint = $("#stocks-company-table").attr("data-href");
        self.tbl = $("#stocks-company-table").DataTable({
          "iDisplayLength": 20,
          "language": {
              processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
          },
          "ajax": {
            "url": self.tbl_endpoint,
            "contentType": "application/json",
            "type": "GET",
            "dataSrc":"",
          },
          "drawCallback": function( settings ) {
            self.handle_domain_change();
          },
          "processing": true,
          "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
          "order": [[ 0, "desc" ]],
          "autoWidth": true,
          "aoColumns": [
            { "mData": "year" },
            { "mData": "substance_name_form" },
            { "mData": "type" },
            { "mData": "is_virgin" },
            { "mData": "result" }
          ],
        });
      }
      if ($("#licences-company-table").length){
        self.tbl_endpoint = $("#licences-company-table").attr("data-href");
        self.tbl = $("#licences-company-table").DataTable({
          "iDisplayLength": 20,
          "language": {
              processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
          },
          "ajax": {
            "url": self.tbl_endpoint,
            "contentType": "application/json",
            "type": "GET",
            "dataSrc":"",
          },
          "drawCallback": function( settings ) {
            self.handle_domain_change();
          },
          "processing": true,
          "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
          "order": [[ 0, "desc" ]],
          "autoWidth": true,
          "aoColumns": [
            { "mData": "year" },
            { "mData": "substance" },
            { "mData": "s_orig_country_name" },
            { "mData": "organization_country_name" },
            { "mData": "use_kind" },
            { "mData": "use_desc" },
            { "mData": "type" },
            { "mData": "quantity" },
          ],
        });
      }
      if ($("#paus-company-table").length){
        self.tbl_endpoint = $("#paus-company-table").attr("data-href");
        self.tbl = $("#paus-company-table").DataTable({
          "iDisplayLength": 20,
          "language": {
              processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
          },
          "ajax": {
            "url": self.tbl_endpoint,
            "contentType": "application/json",
            "type": "GET",
            "dataSrc":"",
          },
          "drawCallback": function( settings ) {
            self.handle_domain_change();
          },
          "processing": true,
          "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
          "order": [[ 0, "desc" ]],
          "autoWidth": true,
          "aoColumns": [
            { "mData": "year" },
            { "mData": "substance" },
            { "mData": "member_state" },
            { "mData": "process_name" },
            { "mData": "pau_use" },
            { "mData": "value" },
            { "mData": "type" },
          ],
        });
      }
    },
    init_matched_companies: function() {
      var self = reportek.utils.fcs;
      if ($('#matching-table').length) {
        self.tbl_endpoint = self.get_endpoint_url('get_candidates');
        self.tbl = $('#matching-table').DataTable({
            "iDisplayLength": 20,
            "language": {
                processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-companies'>Processing...</div>",
            },
            "ajax": {
              "url": self.tbl_endpoint,
              "contentType": "application/json",
              "type": "GET",
              "dataSrc":"",
            },
            "processing": true,
            "aoColumns": [
              { "data": "undertaking.name" },
              { "data": "undertaking.status" },
              { "data": "undertaking.country" },
              { "data": "undertaking.date_updated"}
            ],
            "columnDefs": [
              {
                "width": "40%",
                "targets": 0,
                "data": "undertaking.name",
                "render": function (data, type, full, meta) {
                  return "<a href='" + self.get_endpoint_url('organisation_verification') + "&id=" +
                    full.undertaking.company_id + "'>" + data + "</a>";
                }
              },
              {
                "width": "20%",
                "targets": 1,
              },
              {
                "width": "40%",
                "targets": 2,
              }
            ],
            "order": [[ 0, "asc" ]]
        });
      }
    },
    init_approval_log: function() {
      var self = reportek.utils.fcs;
      if ($('#approval-table').length) {
        self.tbl_endpoint = self.get_endpoint_url('get_matching_log');
        self.tbl = $('#approval-table').DataTable({
            "iDisplayLength": 20,
            "language": {
                processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-approval'>Processing...</div>",
            },
            "ajax": {
              "url": self.tbl_endpoint,
              "contentType": "application/json",
              "type": "GET",
              "dataSrc":"",
            },
            "processing": true,
            "aoColumns": [
              { "data": "company_id" },
              { "data": "verified" },
              { "data": "user" },
              { "data": "timestamp" },
              { "data": "oldcompany_account" },

            ],
            "columnDefs": [
              {
                "width": "20%",
                "targets": 0,
                "render": function (data, type, full) {
                  var result = "<a href='" + self.get_endpoint_url('organisation_details') + "&id=" +
                            full.company_id + "'>" + data + "</a><br/>";
                  return result;
                }
              },
              {
                "width": "20%",
                "targets": 1,
              },
              {
                "width": "20%",
                "targets": 2,
              },
              {
                "width": "20%",
                "targets": 3,
              },
              {
                "width": "20%",
                "targets": 4,
                "render": function (data, type, full) {
                  var result = "N/A";
                  var locked = false;
                  if (data) {
                    var locked_url = self.base_url + '/is_company_locked';
                    $.get( locked_url, { company_id: full.company_id,
                                         old_collection_id: full.oldcompany_account,
                                         country_code: full.country_code,
                                         domain: full.domain }, function(data){
                      locked = data;
                    } );
                    result = "<a class='test_button' href='"
                    if (locked) {
                      result += "unlockCompany?company_id=" + full.company_id + "&old_collection_id=" + full.oldcompany_account + "&country_code=" + full.country_code + "&domain=" + full.domain + "&user=" + full.user + "&came_from=" + window.location.href + "'>Unlock</a><br/>";
                    } else {
                      result += "lockDownCompany?company_id=" + full.company_id + "&old_collection_id=" + full.oldcompany_account + "&country_code=" + full.country_code + "&domain=" + full.domain + "&user=" + full.user + "&came_from=" + window.location.href + "'>Lockdown</a><br/>";
                    }
                  }
                  return result;
                }
              },
            ],
            "order": [[ 0, "asc" ]]
        });
      }
    },
    init_sync_log: function() {
      var self = reportek.utils.fcs;
      if ($('#synclog-table').length) {
        self.tbl_endpoint = self.get_endpoint_url('get_datasync_log');
        self.tbl = $('#synclog-table').DataTable({
            "iDisplayLength": 20,
            "language": {
                processing: "<div class='fcs-loader-container'><img src='++resource++static/ajax-loader.gif' class='fcs-table-loader fcs-table-loader-synclog'>Processing...</div>",
            },
            "ajax": {
              "url": self.tbl_endpoint,
              "contentType": "application/json",
              "type": "GET",
              "dataSrc":"",
            },
            "processing": true,
            "aoColumns": [
              { "data": "execution_time" },
              { "data": "organizations" },
              { "data": "using_last_update" },
            ],
            "columnDefs": [
              {
                "width": "40%",
                "targets": 0,
              },
              {
                "width": "20%",
                "targets": 1,
              },
              {
                "width": "40%",
                "targets": 2,
              }
            ],
            "order": [[ 0, "asc" ]]
        });
      }
    },
};

$(document).ready(function () {
  reportek.utils.fcs.load();
});
