/*global $ */
"use strict";
if (window.reportek === undefined) {
    var reportek = {
        version: "1.0"
    };
}

reportek.utils = {
  users: {},
  countries_keys: {"eu28": ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", 
                             "EE", "ES", "FI", "FR", "GB", "GR", "HR",
                             "HU", "IE", "IT", "LT", "LU", "LV", "MT",
                             "NL", "PL", "PT", "RO", "SE", "SI", "SK"],
                    "eea33": ["AT", "BE", "BG", "CH", "CY", "CZ", "DE",
                              "DK", "EE", "ES", "FI", "FR", "GB", "GR",
                              "HR", "HU", "IE", "IS", "IT", "LI", "LT",
                              "LU", "LV", "MT", "NL", "NO", "PL", "PT",
                              "RO", "SE", "SI", "SK", "TR"],
                    "eionet39": ["AL", "AT", "BA", "BE", "BG", "CH", "CY",
                                 "CZ", "DE", "DK", "EE", "ES", "FI", "FR",
                                 "GB", "GR", "HR", "HU", "IE", "IS", "IT",
                                 "LI", "LT", "LU", "LV", "ME", "MK", "MT",
                                 "NL", "NO", "PL", "PT", "RO", "RS", "SE",
                                 "SI", "SK", "TR", "XK"],
                    "all": []},

  load: function() {
    var self = reportek.utils;
    self.initEnvelopesTable();
    self.initCompaniesTable();
    self.bindSearchRadios();
    var placeholder = "";
    var selects_ids = ["#role", "#obligations", "#countries"];

    for (var i=0; i<=selects_ids.length; i++) {
      var select = $(selects_ids[i]);
      if (select.length > 0) {
        if (select.hasClass("placeholder-enabled")) {
          placeholder = "All";
        }
        select.select2({
          placeholder: placeholder,
          allowClear: true
        });
      }
    }

    if ($("#datatable").length !== 0)
      self.initDataTable();
    $(".toggledCB").click(function() {
      var checkedElems = $(".toggledCB").filter(function(index, element) {
        return $(element).prop("checked") === true;
      });
      if (checkedElems.length === $(".toggledCB").length) {
        $("#toggleAllCB").prop("checked", true);
      } else {
        $("#toggleAllCB").prop("checked", false);
      }
    });
    $(".toggledCB").change(function() {
        self.manage_role_cb(this);
    });
    $("#toggleAllCB").click(function() {
      var toggleAllBtn = $(this);
      var checkBoxes = $(".toggledCB");
      checkBoxes.prop("checked", toggleAllBtn.prop("checked"));
      $.each(checkBoxes, function(index, cb){
        self.manage_role_cb(cb);
      });
    });
    self.manageInfoMessages();
  },

  generateRow: function(row, tableKey) {
    var self = reportek.utils;
    var result = [
        self.renderAsLink(row.path[0], row.path[0], row.path[1]),
        self.renderAsUL($.map(row.obligations, function (obligation) {
          return self.renderAsLink(obligation[0], obligation[1]);
        }))
      ];

    if (tableKey === "by_path")
      result.push(
        self.renderAsUL($.map(row.users, function (user) {
          return self.renderUsersLI(user);
        })));
    else if (tableKey === "by_person")
      result.push(row.user);

    return result;
  },

  renderUsersLI: function(user) {
    var self = reportek.utils;
    var getUserType = $("<a/>", {"class": "user-type",
                                 "data-uid": user.uid,
                                 "href": "api.get_user_type?username=" + user.uid,
                                 "text": "Get user type"});

    return "<span class='user-id'>" + user.uid + "</span>" + self.renderAsUL([getUserType.prop("outerHTML"), "Role: " + user.role]);
  },

  datatable_loading: function(action) {
    var target = $("#datatable");
    var t_parent = target.parent();
    var t_length = $("#datatable_length");
    var t_filter = $("#datatable_filter");
    var t_paginate = $("#datatable_paginate");
    var t_info = $("#datatable_info");
    var img_container = $(".spinner-container");
    if (img_container.length <= 0 ) {
      img_container = $("<div />", {"class": "spinner-container"});
      var img = $("<img />", {
                    "src": "++resource++static/ajax-loader.gif",
                    "class": "ajax-spinner"
                  });
      img_container.append(img);
      t_parent.prepend(img_container);
    }

    if (action === "hide") {
      target.hide();
      t_length.hide();
      t_filter.hide();
      t_paginate.hide();
      t_info.hide();
    } else {
      target.show();
      t_length.show();
      t_filter.show();
      t_paginate.show();
      t_info.show();
      img_container.hide();
    }
  },

  createUserTypeMapping: function() {
    var self = reportek.utils;
    var username;
    $.each($(".user-type"), function(idx, elem) {
      username = $(elem).attr("data-uid");
      if (self.users[username] === undefined) {
        self.users[username] = {"checked": false, "utype": "N/A"};
      }
    });
  },

  updateUserTypeMapping: function(data) {
    var self = reportek.utils;
    var user = JSON.parse(data);
    self.users[user.username].username = user.username;
    self.users[user.username].checked = true;
    self.users[user.username].utype = user.utype;
    self.updateUserType(user.username, user.utype);
  },

  updateUserType: function(user, utype) {
    var text = "Type: " + utype;
    var links = $("[data-uid='" + user + "']");
    var li = links.parent();
    li.html(text);
  },

  getUserType: function(elem) {
    var self = reportek.utils;
    var url = $(elem).attr("href");
    var user = $(elem).attr("data-uid");
    if (self.users[user].checked === true) {
      self.updateUserType(user, self.users[user].utype);
    } else {
      $.ajax({
        url: url,
      }).success(self.updateUserTypeMapping);
    }
  },

  getCurrentUserTypes: function() {
    var self = reportek.utils;
    self.bindGetUserTypes();
    var trows = $("#datatable tbody tr");
    $.each(trows, function(idx, row){
      self.current_row = row;
      var user_type = $(row).find(".user-type");
      var user;
      $.each(user_type, function(i, elem) {
        user = $(elem).attr("data-uid");
        if (self.users[user] === undefined) {
          self.users[user] = {"username": user, "checked": false, "utype": "N/A"};
        }
        self.getUserType(elem);
      });
    });
  },

  bindGetUserTypes: function() {
    var self = reportek.utils;
    var trows = $("#datatable tbody tr");
    $.each(trows, function(idx, elem){
      var user_type = $(elem).find(".user-type");
      $(user_type).on("click", function(evt) {
        evt.preventDefault();
        self.getUserType(this);
      });
    });
  },

  initDataTable: function() {
    /* Init the datatable object */

    var self = reportek.utils;
    var target = $("#datatable");

    var generalSettings = {
      by_path: {
        "columns": [
          {"width": "25%"},
          null,
          {"width": "15%"}
        ]},
      by_person: {
        "ordering": false,
        "drawCallback": function () {
          var api = this.api();
          var rows = api.rows({page: "current"}).nodes();
          var last = null;

          api.column(2, {page:"current"}).data().each(function(group, i) {
            if (last !== group) {
              $(rows).eq(i).before(
                "<tr class='group'><td colspan='2'>" + group + "</td></tr>"
              );
              last = group;
            }
          });
        },
        columnDefs: [
          {"visible": false, "targets": 2}
        ],
        "columns": [
          {"width": "20%"},
          null
        ]
      }
    };

    var dtConfig = {
      pagingType: "simple",
      serverSide: false,
      processing: true,
      pageLength: 100
    };

    var tableKey = target.data("table-key");
    $.extend(dtConfig, generalSettings[tableKey]);
    if (target.hasClass("bdr-datatable") && tableKey === "by_path") {
      dtConfig.columns = [
        {"width": "25%"},
        {"width": "30%"},
        null
      ];
    }
    var dataTable = target.DataTable(dtConfig);
    $(".dataTables_filter input").attr("placeholder", "Filter by...");
    var dataSources = {
      by_path: "/api.get_users_by_path",
      by_person: "/api.get_users"
    };

    self.datatable_loading("hide");
    // $(".placeholder", result).html(img);
    dataTable.on("draw.dt", self.getCurrentUserTypes);
    $.ajax({
      url: dataSources[tableKey],
      data: {
        obligations: $("#obligations").val(),
        role: $("#role").val(),
        countries: $("#countries").val()
      },
      success: function(result) {
        var rows = $.parseJSON(result).data;
        $.each(rows, function(idx, row) {
          dataTable.row.add(self.generateRow(row, tableKey));
        });
        self.datatable_loading("show");
        dataTable.draw();
      }
    });
  },

  manage_role_cb: function(col_cb) {
    var sel_roles = $(col_cb).parents("tr").find(".local-roles");
    if (sel_roles.length > 0) {
      sel_roles.prop("checked", $(col_cb).prop("checked"));
    }
  },

  renderAsUL: function(li_items) {
    var result_html = "";
    $.each(li_items, function(index, li_item) {
      result_html += "<li>" + li_item + "</li>";
    });
    return "<ul>" + result_html + "</ul>";
  },

  clear_filters: function() {
    $("#countries").select2("val", "");
    $("#obligations").select2("val", "");
    $("#role").select2("val", "");
  },

  toggleSelectCountries: function(ckey) {
    /* action can be select or deselect */
    var self = reportek.utils;
    var country_options = $("#countries").find("option");
    var c_len = country_options.length;
    var country_iso;

    if (self.countries_keys.all.length <= 0) {
      var all_countries = [];
      for (var i=0; i<c_len; i++) {
        country_iso = $(country_options[i]).attr("value");
        all_countries.push(country_iso);
        self.countries_keys.all = all_countries;
      }
    }

    var values = $("#s2id_countries").select2("val");
    if (JSON.stringify(values.sort()) === JSON.stringify(self.countries_keys[ckey].sort())) {
      $("#s2id_countries").select2("val", [])  ;
    } else {
      $("#s2id_countries").select2("val", self.countries_keys[ckey]);
    }
  },

  renderAsLink: function(href, display, title) {
    var title_attribute = title ? " title='" + title + "'" : "";
    return "<a href='" + href + "'" + title_attribute + ">" + display + "</a>";
  },

  getUserUrl: function(user) {
    return "http://www.eionet.europa.eu/directory/user?uid=" + user;
  },

  getIMBGClass: function(elem) {
    var bg_class = {
      "msg-info": "bg-info",
      "msg-warning": "bg-warning",
      "msg-danger": "bg-danger",
      "msg-success": "bg-success"
    };
    var elem_classes = elem.attr("class").split(" ");
    return bg_class[elem_classes[elem_classes.length-1]];
  },

  toggleInfoMessage: function(elem) {
    var self = reportek.utils;
    var im_msg = elem.find(".im-message");
    var open_ctl = elem.find(".im-open");
    var close_ctl = elem.find(".im-close");
    if ((im_msg).is(":visible")) {
      elem.removeClass("bg-visible");
      elem.removeClass(self.getIMBGClass(im_msg));
      im_msg.hide();
      close_ctl.hide();
      open_ctl.show();
    } else {
      elem.addClass("bg-visible");
      elem.addClass(self.getIMBGClass(im_msg));
      im_msg.show();
      open_ctl.hide();
      close_ctl.show();
    }
  },

  setCookie: function(elem) {
    var data_info = elem.find(".im-message").attr("data-info");

    if (data_info.length > 0) {
      // Set expire time as per https://developer.mozilla.org/en-US/docs/Web/API/document/cookie
      var cookie = data_info + "=true; ; expires=Fri, 31 Dec 9999 23:59:59 GMT;";
      document.cookie = cookie;
    }
  },

  bindIMControl: function(elem) {
    var self = reportek.utils;
    var open_ctl = elem.find(".im-open");
    var close_ctl = elem.find(".im-close");
    var data_info = elem.find(".im-message").attr("data-info");
    open_ctl.on("click", function(evt){
      self.toggleInfoMessage(elem);
      evt.preventDefault();
    });
    close_ctl.on("click", function(evt){
      self.toggleInfoMessage(elem);
      if (data_info !== undefined) {
        self.setCookie(elem);
      }
      evt.preventDefault();
    });
  },

  manageInfoMessages: function() {
    var self = reportek.utils;
    var info_messages = $(".im-message");
    var data_info, elem;

    for (var i=0; i<info_messages.length; i++) {
      elem = $(info_messages[i]);
      var parent = elem.parent();
      self.bindIMControl(parent);
      data_info = elem.attr("data-info");
      var open_ctl = parent.find(".im-open");
      open_ctl.hide();
      parent.addClass("bg-visible");
      parent.addClass(self.getIMBGClass(elem));
      if (data_info !== undefined) {
        if (data_info.length > 0) {
          if (document.cookie.indexOf(data_info) >= 0) {
            self.toggleInfoMessage(parent);
          }
        }
      }
    }
  },

  initEnvelopesTable: function() {
    $("#env-table").dataTable({
      "order": [[0, "desc"]],
      "aoColumnDefs": [
        {"bSortable": false, "aTargets": [5, 6]}
      ],
      "bAutoWidth": false
    });
  },

  initCompaniesTable: function() {
    $("#comp-table").dataTable({
      "iDisplayLength": 20,
      "sAjaxSource": "/fgases_registry/get_companies",
      "sAjaxDataProp" : "",
      "autowidth": false,
      "order": [[ 0, "desc" ]],
      "columns": [
        { "width": "5%%" },
        { "width": "25%" },
        { "width": "15%" },
        { "width": "13%" },
        { "width": "15%" },
        { "width": "12%" },
        { "width": "15%" }
      ],
      "aoColumns": [
        { "mData": "company_id" },  // for User Detail
        { "mData": "name" },
        { "mData": "domain" },
        { "mData": "users" },
        { "mData": "address.country.name" },
        { "mData": "vat" },
        { "mData": "date_created" }
      ],
      "columnDefs": [
        {
          "width": "25%",
          "targets": 1,
          "data": "name",
          "render": function (data, type, full) {
            return "<a href='/fgases_registry/organisation_details?id=" +
                    full.company_id + "'>" + data + "</a>";
          }
        },
        {
          "width": "13%",
          "targets": 3,
          "data": "users",
          "render": function (data, type, full) {
            var result = "";
            for (var i = 0; i < data.length; i++) {
              result += "<a href='/fgases_registry/organisation_details?id=" +
                        full.company_id + "'>" + data[i].username + "</a><br/>";
            }
            return result;
          }
        }
      ]
    });
  },

  bindSearchRadios: function() {
    var radio_placeholders = {
      "users": "You can search on First name, Surname, Userid and Email",
      "groups": "You can search on LDAP Groups"
    };
    $(".search-radios input").on("click", function(){
      $(".search-box input").attr("placeholder", radio_placeholders[$(this).attr("value")]);
      });
  }

};

window.jQuery(document).ready(function () {
    reportek.utils.load();
});
