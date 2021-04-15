/*global $*/
/*global document*/
/*global window*/
/*jslint browser:true */
"use strict";
if (window.reportek === undefined) {
  var reportek = {
    version: "1.0",
    utils: {}
  };
}

reportek.utils.users = {
  users: {},
  ecas_users: {},
  ecas_paths: {},
  ecas_users_for_query: [],
  ecas_populated: {"grouped_by_path": {},
                   "grouped_by_member": {}},
  table_headers: {"grouped_by_path": ["Collection", "Title", "Obligations", "Users"],
                  "grouped_by_member": ["Path", "Obligations"]},
  table_data: null,
  ecas_roles: ["Reporter (Owner)", "Reader"],
  users_links: {"LDAP User": "www.eionet.europa.eu/directory/user?uid=",
                "LDAP Group": "www.eionet.europa.eu/ldap-roles?role_id="},
  usertype_api: "api.get_user_type?username=",
  userstype_api: "api.get_users_type",
  ecasreportersbypath_api: "api.get_ecas_reporters_by_path",

  load: function() {
    var self = reportek.utils.users;
    $("#datatable").data("table-type", $(".grouping-tabbed-elem.currenttab a").attr("id"));
    self.handleUsersGrouping();
    if ($("#datatable").length !== 0) {
      self.loadResults();
    }
  },

  generateRow: function(row, table_type) {
    var utils = reportek.utils;
    var self = utils.users;
    var klass = row.collection.company_id === null ? "col-path" : "col-path company-col " + row.collection.path.slice(1).split("/").join("-");

    var result = [
        utils.misc.renderAsLink(row.collection.path, row.collection.path, row.collection.title, klass),
        row.collection.title,
        utils.misc.renderAsUL($.map(row.obligations, function (obligation) {
          return utils.misc.renderAsLink(obligation[0], obligation[1]);
        }))
      ];

    if (table_type === "grouped_by_path") {
      result.push(
        utils.misc.renderAsUL($.map(row.users, function (user) {
          return self.renderUsersLI(user);
        }), 'users'));
    }
    else if (table_type === "grouped_by_member") {
      result.push(row.user);
    }
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
    var userFullname = $("<span>", {"class": "user-fullname",
                                   "data-uid": user.uid,
                                   "text": "full name"});
    var userEmail = $("<span>", {"class": "user-email",
                                   "data-uid": user.uid,
                                   "text": "email"});
    return userhtml.outerHTML() +
           ' <small>(' + user.role + ')</small>' +
           utils.misc.renderAsUL([userFullname.outerHTML(),
                                  userEmail.outerHTML(),
                                  getUserType.outerHTML()]);
  },

  createUserTypeMapping: function(user) {
    var self = reportek.utils.users;
    var username;
    $.each($(".user-type"), function(idx, elem) {
      username = $(elem).attr("data-uid");
      if (self.users[username] === undefined) {
        self.users[username] = {"checked": false, "utype": "N/A"};
      }
    });
  },

  updateUserTypeMapping: function(user) {
    var self = reportek.utils.users;
    self.users[user.username].username = user.username;
    self.users[user.username].checked = true;
    self.users[user.username].utype = user.utype;
    self.users[user.username].fullname = user.fullname;
    self.users[user.username].email = user.email;
    self.updateUserType(user.username, user.utype, user.fullname, user.email);
  },

  updateUserType: function(user, utype, fullname, email) {
    var self = reportek.utils.users;
    var users = [];
    var uid_targets;
    var table_type = $("#datatable").data("table-type");
    if (table_type === "grouped_by_path") {
      uid_targets = $("[data-uid='" + user + "']");

      var tags_fullname = uid_targets.filter('.user-fullname');
      if (fullname !== '') {
          tags_fullname.parent().html('<small>' + fullname + '</small>');
      } else {
        tags_fullname.parent().remove();
      }

      var tags_email = uid_targets.filter('.user-email');
      if (email !== '') {
          tags_email.parent().html('<small><a href="mailto:' + email + '">' + email + '</a></small>');
      } else {
        tags_email.parent().remove();
      }

      var text = '<small>Type: ' + utype + '</small>';
      var links = uid_targets.filter('.user-type');
      var li = links.parent();
      li.html(text);
      users = uid_targets.filter(".user-id");
    } else if (table_type === "grouped_by_member") {
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
        url: url
      }).success(function(data) {
        self.updateUserTypeMapping(JSON.parse(data));
      });
    }
  },

  getUsersType: function(users) {
    var self = reportek.utils.users;
    var url = self.userstype_api;
    if (users.length > 0) {
      $.ajax({
        url: url,
        method: 'POST',
        data: {users: users}
        }).done(function(data) {
          var users = JSON.parse(data);
          $.each(users, function(idx, user) {
            self.updateUserTypeMapping(user);
          });
        });
    }
    $.each(self.users, function(idx, user) {
      if (user.checked) {
        self.updateUserTypeMapping(user);
      }
    });
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
      });
    });
    var keys = $.map(self.users, function(v, i){
      if (!v.checked) {
        return i;
      }
    });
    self.getUsersType(keys);
  },

  appendRowUsers: function(row, user) {
    var self = reportek.utils.users;
    var user_ul = $(row).find(".users");
    user_ul.append($("<li>" + self.renderUsersLI(user) + "</li>"));
    if (self.users[user.username] === undefined) {
      self.users[user.username] = user;
      self.users[user.username].checked = true;
      self.users[user.username].utype = "ECAS";
    }
    self.updateUserType(user.username, "ECAS", user.fullname, user.email);
  },

  populateEcasResults: function(page) {
    // Populate the users table td with ecas users
    var self = reportek.utils.users;
    var users = self.ecas_users[page];
    var target = $("#datatable");
    var table_type = target.data("table-type");
    var role = $("#role").val();
    var ddata = [];
    self.ecas_populated[table_type][page] = true;
    for(var path in users) {
      if (users.hasOwnProperty(path)) {
        var klass = path.slice(1).split("/").join("-");
        var row = $("."+klass).parents('tr');
        $.each(users[path], function(idx, user) {
          if (table_type === "grouped_by_member") {
            var record = {};
            record[this.uid] = {"role": this.role,
                                "uid": this.uid};
            ddata.push({"collection": {"path": this.path, "title": this.collection},
                        "obligations": this.obligations,
                        "users": record});
          } else {
            if (user.role === role) {
              self.appendRowUsers(row, user);
            }
          }
        });
        row.find('.spinner-container').css("display", "none");
      }
    }
    if (ddata.length > 0) {
      reportek.utils.spinner.css("display", "block");
      ddata = self.getDataGroupedByMember(ddata);
      var dataTable = target.DataTable();
      var rows = [];
      $.each(ddata, function(idx, row) {
        rows.push(self.generateRow(row, table_type));
      });
      dataTable.rows.add(rows).draw();
      reportek.utils.spinner.css("display", "none");
    }
  },

  getEcasReportersByPath: function(page) {
    var self = reportek.utils.users;
    var url = self.ecasreportersbypath_api;
    var paths = [];
    paths = self.ecas_paths[page];
    if (paths.length > 0) {
      $.ajax({
        url: url,
        method: 'POST',
        data: {paths: paths},
        success: function(data) {
          self.ecas_users[page] = JSON.parse(data);
          self.populateEcasResults(page);
        },
        error: function() {
          $.each($(".company-col"), function(i, elem) {
            paths.push($(elem).text());
            var row = $(elem).parents('tr');
            var user_td = $(row).find(".users").parent();
            $(user_td).find($(".spinner-container")).remove();
            user_td.append($("<span>", {text: "An error occured while retrieving users. Please try again later!"}));
        });
        }
      });
    }
  },

  addReportersSpinnerByPath: function(page) {
    // Retrieve reporters for collections with company id's
    var self = reportek.utils.users;
    var paths = [];
    var col = $(".company-col").text();
    $.each($(".company-col"), function(i, elem) {
      paths.push($(elem).text());
      var row = $(elem).parents('tr');
      var user_td = $(row).find(".users").parent();
      if (user_td.find('.spinner-container').length <= 0) {
        var img_container = $("<div />", {"class": "spinner-container"});
        var img = $("<img />", {
                      "src": "++resource++static/ajax-loader.gif",
                      "class": "ajax-spinner"
                    });
        img_container.append(img);
        user_td.append(img_container);
      }
    });
    self.ecas_paths[page] = paths;
  },

  handleLoadingUsers: function() {
    var self = reportek.utils.users;
    var role = $("#role").val();
    var table = $("#datatable").DataTable();
    var table_type = $(this).data("table-type");
    var page = table.page.info().page;

    if (table_type === 'grouped_by_path') {
      if (self.ecas_roles.indexOf(role) >= 0) {
        $.each($(".company-col"), function(i, elem) {
          if (!self.ecas_paths[page] || self.ecas_paths[page].indexOf($(elem).text()) <= 0) {
            delete self.ecas_users[page];
            return true;
          }
        });
        if (!self.ecas_users[page]) {
          if ($(".spinner-container").length <= 1) {
            self.addReportersSpinnerByPath(page);
            self.getEcasReportersByPath(page);
          }
        }
        if (!self.ecas_populated[table_type][page]) {
          self.populateEcasResults(page);
        }
      }
    self.getCurrentUserTypes();
    } else {
      if (self.ecas_roles.indexOf(role) >= 0 && !self.ecas_populated[table_type]) {
        self.populateEcasResults(page);
        }
      }
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
    dataTable.on("draw.dt", self.handleLoadingUsers);
    $.each(data, function(idx, row) {
      dataTable.row.add(self.generateRow(row, table_type));
    });
    utils.datatable_loading(target, "show");
    dataTable.draw();
  },

  generateDatatableConfig: function(table_type) {
    var generalSettings = {
      grouped_by_path: {
        "columns": [
          {"width": "20%"},
          null,
          null,
          {"width": "25%"}
        ]},
      grouped_by_member: {
        "ordering": false,
        "drawCallback": function () {
          var api = this.api();
          var rows = api.rows({page: "current"}).nodes();
          var last = null;

          api.column(3, {page:"current"}).data().each(function(group, i) {
            if (last !== group) {
              var userhtml = $("<td>", {"colspan": 1,
                                        "data-uid": group.uid,
                                        "class": "user-cell",
                                        "text": group.uid});
              var rolehtml = $("<td>", {"colspan": 1,
                                        "data-uid": group.role,
                                        "class": "user-cell",
                                        "text": 'Role: ' + group.role});
              $(rows).eq(i).before(
                "<tr class='group'>" + userhtml.outerHTML() + rolehtml.outerHTML() + "</tr>"
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
    return dtConfig;
  },

  loadResults: function() {
    /* Retrieve results for get_users_by_path */
    var self = reportek.utils.users;
    var target = $("#datatable");
    var table_type = target.data("table-type");
    reportek.utils.spinner.css("display", "block");

    $.ajax({
      url: "api.get_users_by_path",
      data: {
        obligations: $("#obligations").val(),
        role: $("#role").val(),
        countries: $("#countries").val(),
        path_filter: $("#path_filter").val()
      },
      success: function(result) {
        self.table_data = $.parseJSON(result).data;
        var dtConfig = self.generateDatatableConfig(table_type);
        self.generateDatatable(target, dtConfig, self.table_data, table_type);
      },
      error: function() {
        reportek.utils.spinner.css("display", "none");
        $("#ajax-results").text("An error occured while retrieving results. Please try again later!");
      }
    });
  },

  getDataGroupedByMember: function(data) {
    var self = reportek.utils.users;
    var regrouped = [];
    if (!data) {
      data = self.table_data;
    }
    $.each(data, function(idx, record) {
      var newRec = $.extend({}, record);
      delete newRec.users;
      $.each(record.users, function(index, user) {
        var rr = $.extend({}, newRec);
        rr.user = {'uid': user.uid,
                   'role': user.role};
        regrouped.push(rr);
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
    var info_message = $("#results .info-message > span");
    self.info_text = info_message.text();

    $(".grouping-tabbed-elem a").on("click", function(evt) {
      evt.preventDefault();
      var tab = $(this);
      var data = self.table_data;
      target.data("table-type", tab.attr("id"));
      $(".grouping-tabbed-elem").removeClass("currenttab");
      tab.parent().addClass("currenttab");
      var dtConfig = self.generateDatatableConfig(target.data("table-type"));
      if (target.data("table-type") === "grouped_by_member") {
        data = self.getDataGroupedByMember();
        if (self.ecas_roles.indexOf($("#role").val()) >= 0) {
          $("#results .info-message > span").text("Results related only to our internal user are hidden. ECAS users are not loaded.");
        }
      } else {
        info_message.text(self.info_text);
      }
      self.generateDatatable(target, dtConfig, data, target.data("table-type"));
      self.handleLoadingUsers();
    });
  }
};

$(document).ready(function () {
    reportek.utils.users.load();
});
