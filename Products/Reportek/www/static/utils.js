/*global $, jQuery*/
"use strict";
if (window.reportek === undefined) {
    var reportek = {
        version: "1.0"
    };
}

reportek.utils = {
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
    self.spinner = self.get_spinner($('#results'));
    self.spinner.css('display', 'none');
    self.initEnvelopesTable();
    self.bindSearchRadios();
    self.initTabbedMenu();
    self.bindSyncTransfers();

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

  validate_form: function(form, validate_options) {
    $(form).validate(validate_options);
  },

  get_spinner: function(container) {
    var img_container = container.find($(".spinner-container"));
    if (img_container.length <= 0 ) {
      img_container = $("<div />", {"class": "spinner-container"});
      var img = $("<img />", {
                    "src": "++resource++static/ajax-loader.gif",
                    "class": "ajax-spinner"
                  });
      img_container.append(img);
      container.append(img_container);
    }
    return img_container;
  },

  datatable_loading: function(target, action) {
    var self = reportek.utils;
    var t_id = target.attr("id");
    var t_length = $("#" + t_id+ "_length");
    var t_filter = $("#" + t_id+ "_filter");
    var t_paginate = $("#" + t_id+ "_paginate");
    var t_info = $("#" + t_id+ "_info");

    if (action === "hide") {
      self.spinner.css('display', 'block');
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
      self.spinner.css('display', 'none');
    }
  },

  manage_role_cb: function(col_cb) {
    var sel_roles = $(col_cb).parents("tr").find(".local-roles");
    if (sel_roles.length > 0) {
      sel_roles.prop("checked", $(col_cb).prop("checked"));
    }
  },

  clear_filters: function() {
    $("#countries").select2("val", "");
    $("#obligations").select2("val", "");
    $("#role").select2("val", "");
    $("#path_filter").val("");
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

    if (open_ctl.hasClass("im-ctl-inherit-icon")) {
      open_ctl.css("background-image", close_ctl.css("background-image"));
    };

    var data_info = elem.find(".im-message").attr("data-info");
    open_ctl.off("click").on("click", function(evt){
      self.toggleInfoMessage(elem);
      evt.preventDefault();
    });
    close_ctl.off("click").on("click", function(evt){
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

  bindSearchRadios: function() {
    var radio_placeholders = {
      "users": "You can search on First name, Surname, Userid and Email",
      "groups": "You can search on LDAP Groups"
    };
    $(".search-radios input").on("click", function(){
      $(".search-box input").attr("placeholder", radio_placeholders[$(this).attr("value")]);
      });
  },

  populateUserRolesTable: function(data) {
    var json_data = JSON.parse(data);
    var dtable = $("#ajax-results > .datatable");

    var columnDefs = [ {
          "targets": "dt-country",
          "data": function ( row, type ) {
            if (type === "display" || type === "filter") {
              return row.country;
            }
          },
          "defaultContent": ""
          }, {
          "targets": "dt-path",
          "defaultContent": "",
          "data": function ( row, type ) {
            if(type === "display" || type === "filter") {
              var path = $("<a>", {
                "href": row.path,
                "text": row.path
                });
              return path.outerHTML();
            }
          }
          }, {
          "targets": "dt-obligations",
          "defaultContent": "",
          "data": function ( row, type ) {
            if(type === "display" || type === "filter") {
              var ulist = $("<ul>");
              var li_elem, link;
              for (var i=0; i<row.obligations.length; i++){
                li_elem = $("<li>");
                link = $("<a>", {
                  "href": row.obligations[i].uri,
                  "text": row.obligations[i].title
                  }).appendTo(li_elem);
                li_elem.appendTo(ulist);
              }
              return ulist.outerHTML();
            }
          }
          }, {
          "targets": "dt-roles",
          "defaultContent": "",
          "data": function ( row, type ) {
            if(type === "display" || type === "filter") {
              var username = $("input[name='username']:checked").attr("value");
              var groupsname = $("input[name='groupsname']:checked").attr("value");
              var entity = username ? username : groupsname;
              entity = row.matched_group ? row.matched_group : entity;
              var ulist = $("<ul>");
              var li_elem;
              if (row.roles[entity] !== undefined) {
                for (var i=0; i<row.roles[entity].length; i++){
                  li_elem = $("<li>", {
                    "text": row.roles[entity][i]
                    });
                  li_elem.appendTo(ulist);
                }
              }
              return ulist.outerHTML();
            }
          }
      }];
    var use_subgroups = $("input[name='use-subgroups']:checked").attr("value");
    if (use_subgroups !== undefined) {
      var ldapg_coldef = {
          "targets": "dt-ldap-groups",
          "defaultContent": "",
          "data": function ( row, type ) {
            if(type === "display" || type === "filter") {
              return row.matched_group;
            }
          }
      };
      columnDefs.splice(1, 0, ldapg_coldef);
    }
    dtable.dataTable({
      "data": json_data.data,
      "columnDefs": columnDefs
      });
  },

  handleSearchUser: function(data) {
    var self = reportek.utils;
    var results = $("#ajax-results");

    var coll_form = $("<form>", {
      "id": "coll-form",
      });
    results.html("");

    var user_data = $(data).filter(".datatable");
    user_data.appendTo(coll_form);

    var search_type = $("input[name='search_type']:checked").attr("value");
    if (search_type !== undefined) {
      var hidden_search_type = $("<input>", {
        "type": "hidden",
        "name": "search_type",
        "value": search_type
        });
      hidden_search_type.appendTo(coll_form);
      var use_subgroups = $("input[name='use-subgroups']:checked").attr("value");
      if (use_subgroups !== undefined) {
        var hidden_use_subgroups = $("<input>", {
        "type": "hidden",
        "name": "use-subgroups",
        "value": use_subgroups
        });
        hidden_use_subgroups.appendTo(coll_form);
      }
    }

    if (user_data.length > 0) {
      $("<input>", {
        "type": "submit",
        "name": "btn.find_roles",
        "value": "Find user/group roles"
        }).appendTo(coll_form);
    } else {
      coll_form.append($("<p>", {"text": "No results"}));
    }
    $("#ajax-results").prepend(coll_form);
    $("#coll-form").submit(function(evt){
      evt.preventDefault();
      self.addCollectionDataTable($("#ajax-results"));
      self.datatable_loading($("#ajax-results > .datatable"), "hide");
      $.ajax({
          url: "api.get_collections",
          data: $("#coll-form").serialize(),
          success: function(data){
            $("#coll-table_wrapper").remove();
            self.datatable_loading($("#ajax-results > .datatable"), "show");
            self.populateUserRolesTable(data);
          },
          error: function(){
            $(".ajax-spinner").css("display", "none");
            $("#ajax-results").text("An error occured while retrieving results. Please try again later!");
          }
      });
    });
  },

  addCollectionDataTable: function(parent_el) {
    var theading = [
      ["Country", "dt-country"],
      ["Path", "dt-path"],
      ["Obligations", "dt-obligations"],
      ["Roles", "dt-roles"]
    ];
    var use_subgroups = $("input[name='use-subgroups']:checked").attr("value");
    if (use_subgroups !== undefined) {
      theading.splice(1, 0, ["LDAP Groups", "dt-ldap-groups"]);
    }
    var dtable = $("<table>", {
        "id": "coll-table",
        "class": "datatable"
      }).appendTo(parent_el);
    var dthead = $("<thead>").appendTo(dtable);
    var headrow = $("<tr>").appendTo(dthead);
    for (var i=0; i<theading.length; i++) {
      headrow.append($("<th>", {
        "text": theading[i][0],
        "class": theading[i][1]
        }));
    }
  },

  initTabbedMenu: function() {
    var self = reportek.utils;
    $(".ajaxtabsmenu a").on("click", function(evt) {
      var tab = $(this);

      $(".tabbed-content").addClass("hidden-content");
      $(".tabbed-elem").removeClass("currenttab");

      $(tab.attr("href")).removeClass("hidden-content");
      tab.parent().addClass("currenttab");

      $("#results").find('*').not(".spinner-container, .spinner-container *").remove();
      $("#ajax-results").empty();

      evt.preventDefault();
    });

    $(".filter-form #find-user-form").submit(function(evt) {
      evt.preventDefault();
      $("#ajax-results").empty();
      self.spinner.css("display", "block");
      $.ajax({
          url: "find_user",
          data: $("#find-user-form").serialize(),
          success: function(data){
            self.spinner.css("display", "none");
            reportek.utils.handleSearchUser(data);
          },
          error: function(){
            $(".ajax-spinner").css("display", "none");
            $("#ajax-results").text("An error occured while retrieving results. Please try again later!");
          }
        });
    });
  },

  bindSyncTransfers: function() {
    var self = reportek.utils;
    $(".sync-transfers").on("click", function(evt) {
      var cb = $(this).parents('tr').find('input[name="collections:list"]');
      cb.prop('checked', $(this).prop('checked'));
    });
  },
};

window.jQuery(document).ready(function () {
    jQuery.fn.outerHTML = function(s) {
      return s ? this.before(s).remove() : jQuery("<p>").append(this.eq(0).clone()).html();
    };
    reportek.utils.load();
});
