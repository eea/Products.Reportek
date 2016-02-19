/*global $*/
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.users = {
  users: {},
  table_headers: {"grouped_by_path": ["Collection", "Title", "Obligations", "Users"],
                  "grouped_by_person": ["Path", "Obligations"]},
  table_data: null,
  users_links: {"LDAP User": "www.eionet.europa.eu/directory/user?uid=",
                "LDAP Group": "www.eionet.europa.eu/ldap-roles?role_id="},
  usertype_api: "api.get_user_type?username=",

  load: function() {
    var self = reportek.utils.users;
    $("#datatable").data("table-type", $(".grouping-tabbed-elem.currenttab a").attr("id"));
    self.handleUsersGrouping();
    if ($("#datatable").length !== 0)
      self.loadResults();
  },


  generateRow: function(row, table_type) {
    var utils = reportek.utils;
    var self = utils.users;
    var result = [
        utils.misc.renderAsLink(row.collection.path, row.collection.path, row.collection.title),
        row.collection.title,
        utils.misc.renderAsUL($.map(row.obligations, function (obligation) {
          return utils.misc.renderAsLink(obligation[0], obligation[1]);
        }))
      ];

    if (table_type === "grouped_by_path")
      result.push(
        utils.misc.renderAsUL($.map(row.users, function (user) {
          return self.renderUsersLI(user);
        })));
    else if (table_type === "grouped_by_person")
      result.push(row.user);

    return result;
  },

  renderUsersLI: function(user) {
    var utils = reportek.utils;
    var self = utils.users;
    var getUserType = $("<a/>", {"class": "user-type",
                                 "data-uid": user.uid,
                                 "href": self.usertype_api + user.uid,
                                 "text": "Get user type"});
    var userhtml = $("<span>", {"class": "user-id",
                                "data-uid": user.uid,
                                "text": user.uid});
    return userhtml.outerHTML() + utils.misc.renderAsUL([getUserType.prop("outerHTML"), "Role: " + user.role]);
  },

  createUserTypeMapping: function() {
    var self = reportek.utils.users;
    var username;
    $.each($(".user-type"), function(idx, elem) {
      username = $(elem).attr("data-uid");
      if (self.users[username] === undefined) {
        self.users[username] = {"checked": false, "utype": "N/A"};
      }
    });
  },

  updateUserTypeMapping: function(data) {
    var self = reportek.utils.users;
    var user = JSON.parse(data);
    self.users[user.username].username = user.username;
    self.users[user.username].checked = true;
    self.users[user.username].utype = user.utype;
    self.updateUserType(user.username, user.utype);
  },

  updateUserType: function(user, utype) {
    var self = reportek.utils.users;
    var tab_sel = $(".grouping-tabbed-elem.currenttab");
    var users = [];
    var uid_targets;
    if (tab_sel.find('#grouped_by_path').length > 0) {
      var text = "Type: " + utype;
      uid_targets = $("[data-uid='" + user + "']");
      var links = uid_targets.filter('.user-type');
      var li = links.parent();
      li.html(text);
      users = uid_targets.filter(".user-id");
    } else if (tab_sel.find("#grouped_by_person").length > 0) {
      users = $("[data-uid='" + user + "']");
    }
    if ((utype === "LDAP Group" || utype === "LDAP User") && users.length > 0) {
      var user_link = $("<a>", {"class": "user-link",
                                "href": window.location.protocol + "//" + self.users_links[utype] + user,
                                "target": "_blank",
                                "text": user});
      users.html(user_link.outerHTML());
    }
  },

  getUserType: function(elem) {
    var self = reportek.utils.users;
    var user = $(elem).attr("data-uid");
    var url = self.usertype_api + user;
    if (self.users[user].checked === true) {
      self.updateUserType(user, self.users[user].utype);
    } else {
      $.ajax({
        url: url,
      }).success(self.updateUserTypeMapping);
    }
  },

  getCurrentUserTypes: function() {
    var self = reportek.utils.users;
    self.bindGetUserTypes();
    var trows = $("#datatable tbody tr");
    $.each(trows, function(idx, row){
      self.current_row = row;
      var user_type = $(row).find(".user-type,.user-cell");
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
    var self = reportek.utils.users;
    var trows = $("#datatable tbody tr");
    $.each(trows, function(idx, elem){
      var user_type = $(elem).find(".user-type");
      $(user_type).on("click", function(evt) {
        evt.preventDefault();
        self.getUserType(this);
      });
    });
  },

  generateDTHeaders: function(target, table_type){
    var self = reportek.utils.users;
    var thead = $("<thead>");
    thead.appendTo(target);
    var rowhead = $("<tr>").appendTo(thead);
    $.each(self.table_headers[table_type], function(idx, header){
      rowhead.append($("<th>", {text: header}));
    });
    target.append($("<tbody>"));
  },

  generateDatatable: function(target, dtConfig, data, table_type) {
    var utils = reportek.utils;
    var self = utils.users;

    target.empty();
    self.generateDTHeaders(target, table_type);
    dtConfig.destroy = true;

    var dataTable = target.DataTable(dtConfig);
    dataTable.clear();

    $(".dataTables_filter input").attr("placeholder", "Filter by...");
    utils.datatable_loading(target, "hide");
    dataTable.on("draw.dt", self.getCurrentUserTypes);
    $.each(data, function(idx, row) {
      dataTable.row.add(self.generateRow(row, table_type));
    });
    utils.datatable_loading(target, "show");
    dataTable.draw();
  },

  generateDatatableConfig: function(table_type, dr_type) {
    var generalSettings = {
      grouped_by_path: {
        "columns": [
          {"width": "25%"},
          null,
          null,
          {"width": "15%"}
        ]},
      grouped_by_person: {
        "ordering": false,
        "drawCallback": function () {
          var api = this.api();
          var rows = api.rows({page: "current"}).nodes();
          var last = null;

          api.column(3, {page:"current"}).data().each(function(group, i) {
            if (last !== group) {
              var userhtml = $("<td>", {"colspan": 2,
                                        "data-uid": group,
                                        "class": "user-cell",
                                        "text": group});
              $(rows).eq(i).before(
                "<tr class='group'>" + userhtml.outerHTML() + "</tr>"
              );
              last = group;
            }
          });
        },
        columnDefs: [
          {"visible": false, "targets": [1,3]}
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

    $.extend(dtConfig, generalSettings[table_type]);
    if (dr_type === 'BDR' && table_type === "grouped_by_path") {
      dtConfig.columns = [
        {"width": "25%"},
        {"width": "30%"},
        null
      ];
    }
    return dtConfig;
  },

  loadResults: function() {
    /* Retrieve results for get_users_by_path */
    var self = reportek.utils.users;
    var target = $("#datatable");
    var table_type = target.data("table-type");
    var dr_type = target.data("table-dr_type");

    $.ajax({
      url: "/api.get_users_by_path",
      data: {
        obligations: $("#obligations").val(),
        role: $("#role").val(),
        countries: $("#countries").val(),
        path_filter: $("#path_filter").val()
      },
      success: function(result) {
        self.table_data = $.parseJSON(result).data;
        var dtConfig = self.generateDatatableConfig(table_type, dr_type);
        self.generateDatatable(target, dtConfig, self.table_data, table_type);
      }
    });
  },

  getDataGroupedByPerson: function() {
    var self = reportek.utils.users;
    var regrouped = [];
    $.each(self.table_data, function(idx, record) {
      var newRec = $.extend({}, record);
      delete newRec.users;
      $.each(record.users, function(index, user) {
        newRec.user = user.uid;
        regrouped.push(newRec);
      });
    });
    regrouped.sort(function(a, b){
      return a.user == b.user ? 0 : +(a.user > b.user) || -1;
    });
    return regrouped;
  },

  handleUsersGrouping: function() {
    var self = reportek.utils.users;
    var target = $("#datatable");
    var dr_type = target.data("table-dr_type");

    $(".grouping-tabbed-elem a").on("click", function(evt) {
      evt.preventDefault();
      var tab = $(this);
      var data = self.table_data;
      target.data("table-type", tab.attr("id"));
      $(".grouping-tabbed-elem").removeClass("currenttab");
      tab.parent().addClass("currenttab");
      var dtConfig = self.generateDatatableConfig(target.data("table-type"), dr_type);
      if (target.data("table-type") === "grouped_by_person") {
        data = self.getDataGroupedByPerson();
      }
      self.generateDatatable(target, dtConfig, data, target.data("table-type"));
    });
  }
};

$(document).ready(function () {
    reportek.utils.users.load();
});
