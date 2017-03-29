/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.autocomplete = {
    load: function() {
      var self = reportek.utils.autocomplete;
      $("#workflow").on("change", function() {
        var selected = $(this).find(":selected");
        var results = selected.data()['results'];
        var task = $("#task :selected").val();
        var wfresults = results[task];
        var inspectvals = [];
        for (var prop in wfresults) {
          inspectvals.push(wfresults[prop]);
        }
        inspectvals.sort();
        inspectvals = $.unique(inspectvals);
        var resultsselect = $("#inspectresult");
        resultsselect.empty();
        $.each(inspectvals, function( index, value ) {
          if (value !== null) {
            $( "<option></option>", {
              "value": value,
              "text": value
              }).appendTo(resultsselect);
          }
        });
      });
      $("#task").on("change", function() {
        self.populateWFSelect();
      });
      self.populateWFSelect();
    },
    populateWFSelect: function() {
      var selected = $("#task").find(":selected");
      if (selected.length > 0) {
        var workflows = selected.data()["workflows"];
        if (workflows.length > 0) {
          workflows = workflows.split(',')
        }
        var wfoptions = $("#workflow > option");
        for (var i=0; i < wfoptions.length; i++) {
            $(wfoptions[i]).addClass("hidden-content");
            if (workflows.indexOf(wfoptions[i].value) != -1) {
                $(wfoptions[i]).removeClass("hidden-content");
            }
        }
        var visible = $("#workflow > option").not('.hidden-content');
        if (visible.length > 0) {
            $(visible[0]).prop("selected", true);
            $("#workflow").trigger("change");
        }
      }
    }
}

$(document).ready(function () {
    reportek.utils.autocomplete.load();
});
