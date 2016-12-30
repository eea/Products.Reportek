/*global $, jQuery*/
"use strict";

window.jQuery(document).ready(function () {
    jQuery.fn.outerHTML = function(s) {
      return s ? this.before(s).remove() : jQuery("<p>").append(this.eq(0).clone()).html();
    };
    var elems = $(".select2-enabled");
    var placeholder = "";
    for (var i=0; i<=elems.length; i++) {
      var select = $(elems[i]);
      if (select.length > 0) {
        if (select.hasClass("placeholder-enabled")) {
          placeholder = "All";
        }
        select.select2({
          placeholder: placeholder,
          allowClear: true,
          matcher: function(term, text, option) {
            return text.toUpperCase().indexOf(term.toUpperCase())>=0 || option.val().toUpperCase().indexOf(term.toUpperCase())>=0;
          }
        });
      }
    }
    // if (select.hasClass("placeholder-enabled")) {
    //   placeholder = "All";
    // }
    // $(".select2enabled").select2({
    //   placeholder: placeholder,
    //   allowClear: true,
    //   matcher: function(term, text, option) {
    //     return text.toUpperCase().indexOf(term.toUpperCase())>=0 || option.val().toUpperCase().indexOf(term.toUpperCase())>=0;
    //   }
    // });
});
