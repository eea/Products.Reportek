/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.misc = {
  renderAsUL: function(li_items) {
    var result_html = "";
    $.each(li_items, function(index, li_item) {
      result_html += "<li>" + li_item + "</li>";
    });
    return "<ul>" + result_html + "</ul>";
  },

  renderAsLink: function(href, display, title) {
    var title_attribute = title ? " title='" + title + "'" : "";
    return "<a href='" + href + "'" + title_attribute + ">" + display + "</a>";
  },

  labelWrap: function(input, label_text, title) {
    return $("<label>", {"title": title}).append(input, label_text);
  },

  renderAsRadio: function(name, value, display, title, checked, klass) {
    var self = reportek.utils.misc;
    var radio = $("<input>", {
        type: "radio",
        name: name,
        value: value,
        class: klass,
      });
    if (checked !== 0) {
      radio.attr("checked", "checked");
    }
    return self.labelWrap(radio, display, title).outerHTML();
  }
};
