/*global $, jQuery*/
/*global document*/
/*global window*/
/*jslint browser:true */
/* jslint:disable */
/* Paging, sorting and per column filtering for the engine's
   "Obligation locks" table. */
"use strict";

(function ($) {
  // Column index -> kind of filter.
  var FILTERS = {
    2: "text", // Id
    3: "text", // Obligation
    4: "select", // ROD status
    5: "select", // Kind
    6: "select", // Strength
    7: "text", // Window
    8: "select", // State
    9: "text", // Reason
    10: "select", // Workflow
    11: "select", // Dataflow mapping records
    12: "text", // Exempt paths
    13: "text" // Locked
  };

  function cellText(html) {
    return $("<div>").html(html).text().trim();
  }

  // Comma separated cells contribute each of their values.
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
    // The filters sit inside the removal form: never submit it.
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

  // Rows on other pages are detached, so their checked boxes never submit.
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

  // Both dialogs add and edit; editing carries the obligation in edit_uri.
  function prepareLockDialog(modal, lock) {
    var form = modal.find("form");
    form[0].reset();
    // Placeholder, not value: an untouched box stores nothing, so the
    // translated default is what reporters actually get.
    modal.find(".lock-default-reason").each(function () {
      var offered = $(this);
      form
        .find("[name='" + offered.data("for") + "']")
        .attr("placeholder", offered.text().replace(/\s+/g, " ").trim());
    });
    // select2 only notices a reset on change.
    form.find(".select2-enabled").trigger("change");
    form.find("[name='edit_uri']").val(lock ? lock.uri : "");
    modal.find(".lock-obligation-picker").toggle(!lock);
    modal.find(".lock-obligation-fixed").toggle(Boolean(lock));
    var labels = modal.find(".lock-labels");
    modal.find(".modal-title").text(labels.data(lock ? "edit-title" : "add-title"));
    modal.find(".lock-submit").val(labels.data(lock ? "edit-label" : "add-label"));
    if (!lock) {
      return;
    }
    modal.find(".lock-obligation-name").text(lock.label);
    ["reason", "reason_manager", "reason_anonymous", "target_url",
     "open_from", "open_until", "reporting_year", "strength",
     "year_basis"].forEach(function (name) {
      form.find("[name='" + name + "']").val(lock[name]);
    });
    form.find("[name='exempt_paths']").val((lock.exempt_paths || []).join("\n"));
  }

  $(function () {
    $(".lock-modal").on("show.bs.modal", function (event) {
      prepareLockDialog($(this), $(event.relatedTarget).data("lock") || null);
    });

    var element = $("#locks-table");
    if (!element.length) {
      return;
    }

    var table = element.DataTable({
      pageLength: 25,
      lengthMenu: [10, 25, 50, 100],
      order: [[3, "asc"]],
      orderCellsTop: true,
      autoWidth: false,
      columnDefs: [
        {targets: [0, 1], orderable: false, searchable: false}
      ]
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
