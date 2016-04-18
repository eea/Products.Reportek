/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.referrals = {
  table_headers: ["Collection", "Title", "Obligations", "Referrals"],

  load: function() {
    var self = reportek.utils.referrals;
    self.bind_search_submit();
  },

  bind_search_submit: function() {
    var self = reportek.utils.referrals;
    $("#referrals_filters").on("submit", function(evt){
      evt.preventDefault();
      var formdata = $(this).serialize();

      $.ajax({
          url: "api.get_referrals_status",
          data: formdata
      }).success(self.update_results);
    });
  },

  update_results: function(data) {
    var self = reportek.utils.referrals;
    var target = $("#datatable");
    reportek.utils.spinner.css("display", "block");
    self.table_data = $.parseJSON(data).data;
    var dtConfig =  {
        "columns": [
          {"width": "25%"},
          null,
          null,
          {"width": "15%"}
        ],
        pagingType: "simple",
        serverSide: false,
        processing: true,
        pageLength: 100
        };
    self.generateDatatable(target, dtConfig, self.table_data);
    if (self.table_data.length > 0) {
      $("#results").find("input[type='submit']").removeClass("hidden-content");
    } else {
      $("#results").find("input[type='submit']").addClass("hidden-content");
    }
  },

  generateRow: function(row) {
    var utils = reportek.utils;
    var result = [
        utils.misc.renderAsLink(row.path, row.path, row.title),
        row.title,
        utils.misc.renderAsUL($.map(row.obligations, function (obligation) {
          return utils.misc.renderAsLink(obligation.uri, obligation.title);
        }))
      ];
    var allowed = '';
    if (row.prop_allowed_referrals === null) {
      allowed = utils.misc.renderAsCheckbox('allowed_referrals', row.path, 'Inherited', row.allowed_referrals);
    } else {
      allowed = utils.misc.renderAsCheckbox('allowed_referrals', row.path, '', row.allowed_referrals);
    }
    result.push(allowed);
    return result;
  },

  generateDTHeaders: function(target){
    var self = reportek.utils.referrals;
    var thead = $("<thead>");
    thead.appendTo(target);
    var rowhead = $("<tr>").appendTo(thead);
    $.each(self.table_headers, function(idx, header){
      rowhead.append($("<th>", {text: header}));
    });
    target.append($("<tbody>"));
  },

  generateDatatable: function(target, dtConfig, data) {
    var utils = reportek.utils;
    var self = utils.referrals;

    target.empty();
    self.generateDTHeaders(target);
    dtConfig.destroy = true;

    var dataTable = target.DataTable(dtConfig);
    dataTable.clear();

    $(".dataTables_filter input").attr("placeholder", "Filter by...");
    utils.datatable_loading(target, "hide");
    $.each(data, function(idx, row) {
      dataTable.row.add(self.generateRow(row));
    });
    utils.datatable_loading(target, "show");
    dataTable.draw();
  },
};

$(document).ready(function () {
  reportek.utils.referrals.load();
});
