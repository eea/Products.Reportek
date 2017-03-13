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
        var results = selected.data()['results'].split(',');
        var resultsselect = $("#inspectresult");
        resultsselect.empty();
        $.each(results, function( index, value ) {
          $( "<option></option>", {
            "value": value,
            "text": value
            }).appendTo(resultsselect);
        });
      });
      $("#task").on("change", function() {
        var selected = $(this).find(":selected");
        var workflows = selected.data()["workflows"].split(',');
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
      });
    }
}

$(document).ready(function () {
    reportek.utils.autocomplete.load();
});
