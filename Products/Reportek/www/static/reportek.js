/*global $, jQuery*/
/*global document*/
/*global window*/
/*jslint browser:true */
/* jslint:disable */
"use strict";

window.jQuery(document).ready(function () {
    jQuery.fn.outerHTML = function(s) {
      return s ? this.before(s).remove() : jQuery("<p>").append(this.eq(0).clone()).html();
    };
    function escapeHtml(text) {
      return jQuery('<div/>').text(text).html();
    }

    function isTerminatedOption(option) {
      return option && option.element &&
        jQuery(option.element).hasClass("terminated");
    }

    function formatSelect2Option(option) {
      var text = escapeHtml(option.text);
      if (isTerminatedOption(option)) {
        return text + '<span class="terminated-label">(Terminated)</span>';
      }
      return text;
    }

    function formatSelect2OptionClass(option) {
      return isTerminatedOption(option) ? "terminated-result" : "";
    }

    function highlightTerminatedSelect2(select) {
      var container = jQuery("#s2id_" + select.attr("id"));
      var selected = select.find("option:selected");
      var isTerminated = selected.hasClass("terminated");
      container.toggleClass("terminated-selected", isTerminated);
      container.find(".terminated-label").remove();
      if (isTerminated) {
        container.find(".select2-chosen").append(
          '<span class="terminated-label">(Terminated)</span>'
        );
      }
    }

    var elems = $(".select2-enabled");
    for (var i=0; i<=elems.length; i++) {
      var select = $(elems[i]);
      if (select.length > 0) {
        select.select2({
          allowClear: true,
          formatResult: formatSelect2Option,
          formatResultCssClass: formatSelect2OptionClass,
          matcher: function(term, text, option) {
            return text.toUpperCase().indexOf(term.toUpperCase())>=0 || option.val().toUpperCase().indexOf(term.toUpperCase())>=0;
          }
        });
        highlightTerminatedSelect2(select);
        select.on("change", function () {
          highlightTerminatedSelect2(jQuery(this));
        });
      }
    }
    $("input[type='reset']").click(function (){
      var elems = $(".select2-enabled");
      elems.val([]).trigger('change');
    });

    $(".select2-enabled").on('change', function (e) {
      var sync_process = $("input[name='sync_process']");
      if (sync_process.length) {
        if (sync_process.prop('disabled')) {
          sync_process.prop("disabled", false);
        }
      }
    });
});
