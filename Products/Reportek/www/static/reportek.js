/*global $, jQuery*/
"use strict";

window.jQuery(document).ready(function () {
    jQuery.fn.outerHTML = function(s) {
      return s ? this.before(s).remove() : jQuery("<p>").append(this.eq(0).clone()).html();
    };
    var elems = $(".select2-enabled");
    for (var i=0; i<=elems.length; i++) {
      var select = $(elems[i]);
      if (select.length > 0) {
        select.select2({
          allowClear: true,
          matcher: function(term, text, option) {
            return text.toUpperCase().indexOf(term.toUpperCase())>=0 || option.val().toUpperCase().indexOf(term.toUpperCase())>=0;
          }
        });
      }
    }
    $("input[type='reset']").click(function (){
      var elems = $(".select2-enabled");
      elems.val([]).trigger('change');
    });
});
