/*global $, jQuery*/
/*global document*/
/*global window*/
/*jslint browser:true */
/* jslint:disable */
/* Paging, sorting and per column filtering for the engine's
   "Obligation locks" table. */
"use strict";

(function ($) {
  // Column index -> kind of filter. The first column holds the checkboxes,
  // so it gets neither a filter nor sorting.
  var FILTERS = {
    1: "text", // Id
    2: "text", // Obligation
    3: "select", // ROD status
    4: "select", // Kind
    5: "select", // Strength
    6: "text", // Window
    7: "select", // State
    8: "text", // Reason
    9: "select", // Workflow
    10: "select", // Dataflow mapping records
    11: "text", // Exempt paths
    12: "text" // Locked
  };

  function cellText(html) {
    return $("<div>").html(html).text().trim();
  }

  // Distinct values of a column. Cells listing several values separated by
  // commas, such as the workflow one, contribute each of them.
  function distinctValues(column) {
    var seen = {};
    column.data().each(function (html) {
      cellText(html)
        .split(/,\s*/)
        .forEach(function (value) {
          value = value.trim();
          if (value) {
            seen[value] = true;
          }
        });
    });
    return Object.keys(seen).sort();
  }

  function buildFilter(table, column, kind, cell) {
    var control;
    if (kind === "select") {
      control = $('<select><option value=""></option></select>');
      distinctValues(column).forEach(function (value) {
        control.append($("<option>").val(value).text(value));
      });
    } else {
      control = $('<input type="text" />').attr(
        "placeholder",
        cellText(cell.html())
      );
    }
    // The filters sit inside the removal form: keep them nameless so they
    // are never submitted, and swallow Enter so they never submit it.
    control.on("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
      }
    });
    control.on("change keyup", function () {
      var value = $(this).val();
      if (column.search() !== value) {
        column.search(value).draw();
      }
    });
    cell.empty().append(control);
  }

  // Rows on other pages are detached from the document, so their checked
  // boxes would never reach the server. Carry them in hidden inputs.
  function carrySelectionAcrossPages(table, form) {
    $(form).on("submit", function () {
      $(".carried-selection", form).remove();
      table.$("input[name='uris:list']:checked").each(function () {
        if (!$.contains(document, this)) {
          $("<input>", {
            type: "hidden",
            name: "uris:list",
            value: this.value,
            "class": "carried-selection"
          }).appendTo(form);
        }
      });
    });
  }

  // The obligation pickers live inside Bootstrap modals and need nothing
  // extra: select2 3.5 puts its dropdown inside its own container, so it
  // stays within the dialog and the modal's focus trap leaves it alone.
  $(function () {
    var element = $("#locks-table");
    if (!element.length) {
      return;
    }

    var table = element.DataTable({
      pageLength: 25,
      lengthMenu: [10, 25, 50, 100],
      order: [[2, "asc"]],
      orderCellsTop: true,
      autoWidth: false,
      columnDefs: [{targets: 0, orderable: false, searchable: false}]
    });

    var filterRow = element
      .find("thead tr")
      .first()
      .clone()
      .addClass("filters")
      .appendTo(element.find("thead"));

    filterRow.find("th").each(function (index) {
      var kind = FILTERS[index];
      if (kind) {
        buildFilter(table, table.column(index), kind, $(this));
      } else {
        $(this).empty();
      }
    });

    carrySelectionAcrossPages(table, $("form[name='locks']")[0]);
  });
})(jQuery);
