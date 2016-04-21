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
    self.bind_submits();
  },

  bind_submits: function() {
    var self = reportek.utils.referrals;
    $("#referrals_filters").on("submit", function(evt){
      evt.preventDefault();
      var valid_obj = {
          ignore: '',
          rules: {
            "obligations:list": { required:true }
          },
          messages: {
            "obligations:list": {
              required: 'Required field'
            }
          },
          highlight: function(label) {
            $(label).closest('.control-group').addClass('err');
          },
          success: function (label, element) {
            label.text('').closest('.control-group').removeClass('err');
          },
      };

      reportek.utils.validate_form(this, valid_obj);

      if ($(this).valid()) {
        reportek.utils.spinner.css("display", "block");
        var formdata = $(this).serialize();

        $.ajax({
            url: "api.get_referrals_status",
            data: formdata
        }).success(self.update_results);
      }
    });

    $("#update_referrals").on("submit", function(evt) {
      evt.preventDefault();
      var formdata = $(this).serialize();
      $.ajax({
          url: "api.update_referrals_status",
          data: formdata
      }).success(self.update_apply_results);
    });
  },
  
  update_results: function(data) {
    var self = reportek.utils.referrals;
    var target = $("#datatable");
    self.table_data = $.parseJSON(data).data;
    var dtConfig =  {
        "columns": [
          {"width": "25%"},
          null,
          null,
          {"width": "27%"}
        ],
        pagingType: "simple",
        serverSide: false,
        processing: true,
        pageLength: 100
        };
    self.generateDatatable(target, dtConfig, self.table_data);
    var warn_container = $(".warning-container");
    if (self.table_data.length > 0) {
      $("#results").find("input[type='submit']").removeClass("hidden-content");
      if (warn_container.hasClass("hidden-content")) {
        $(".warning-container").removeClass("hidden-content");
        reportek.utils.manageInfoMessages();
      }
    } else {
      $("#results").find("input[type='submit']").addClass("hidden-content");
    }
  },

  update_apply_results: function(data) {
    var uresults = $.parseJSON(data);
    var container;
    $(".upd-success").removeClass("upd-success");
    $(".upd-error").removeClass("upd-error");
    $(".upd").remove();
    if (uresults.updated.length > 0) {
      $.each(uresults.updated, function(index, elem) {
        container = $("input[name='rstatus:" + elem.rid + "']").parent();
        var acquired = container.find(".acquired-setting");
        if (acquired) {
          acquired.removeClass("acquired-setting icon-double-angle-down");
          acquired.addClass("explicit-setting icon-double-angle-right upd-success");
        }
        $("<span>", {
          "class": "upd upd-success icon-ok-sign",
          "title": "Updated successfully"
        }).appendTo(container);
      });
    }
    if (uresults.errors.length > 0) {
      $.each(uresults.errors, function(index, elem) {
        container = $("input[name='rstatus:" + elem.rid + "']").parent();
        $("<span>", {
          "class": "upd upd-error icon-remove-sign",
          "title": elem.error
        }).appendTo(container);
      });
    }
    $("html, body").animate({scrollTop: $(".upd").first().offset().top}, "fast");
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

    var setting_type = $("<span>", {
        "class": row.prop_allowed_referrals === null ? "acquired-setting icon-double-angle-down" : "explicit-setting icon-double-angle-right",
      });
    var allowed = setting_type.outerHTML();

    var settings = ['1', '0'];
    $.each(settings, function(index, setting) {
      var name = 'rstatus:' + row.rid;
      var display = setting === '1' ? 'Allowed' : 'Not allowed';
      var checked = setting === '1' && row.allowed_referrals !== 0 || setting === '0' && row.allowed_referrals === 0 ? 'checked' : 0;
      allowed += utils.misc.renderAsRadio(name, setting, display, checked, 'referrals-status');
    });

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
