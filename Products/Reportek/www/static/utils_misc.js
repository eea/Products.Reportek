/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.misc = {
  renderAsUL: function(li_items, klass, iklass) {
    var result_html = "";
    var u_class_attribute = klass ? " class='" + klass + "'" : "";
    var i_class_attribute = iklass ? " class='" + iklass + "'" : "";
    $.each(li_items, function(index, li_item) {
      result_html += "<li" + i_class_attribute + ">" + li_item + "</li>";
    });
    return "<ul" + u_class_attribute + ">" + result_html + "</ul>";
  },

  renderAsLink: function(href, display, title, klass) {
    var title_attribute = title ? " title='" + title + "'" : "";
    var class_attribute = klass ? " class='" + klass + "'" : "";
    return "<a href='" + href + "'" + title_attribute + class_attribute + ">" + display + "</a>";
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
