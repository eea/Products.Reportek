function generateRow(row, tableKey) {

  var result = [
      renderAsLink(row.path[0], row.path[0], row.path[1]),
      renderAsUL($.map(row.obligations, function (obligation) {
        return renderAsLink(obligation[0], obligation[1]);
      }))
    ];

  if (tableKey === 'by_path')
    result.push(
      renderAsUL($.map(row.users, function (user) {
        return renderUsersLI(user);
      })));
  else if (tableKey === 'by_person')
    result.push(row.user);

  return result;
}

function renderUsersLI(user) {
  return renderAsLink(getUserUrl(user.uid), user.uid) + renderAsUL(['Type: ' + user.type, 'Role: ' + user.role]);
}

function initEnvelopesTable() {
  $("#env-table").dataTable({
    "order": [[0, "desc"]],
    "aoColumnDefs": [
      {'bSortable': false, 'aTargets': [5, 6]}
    ],
    "bAutoWidth": false
  });
}

function initCompaniesTable() {
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
        "render": function (data, type, full, meta) {
          return '<a href="/fgases_registry/organisation_details?id='
            + full.company_id + '">' + data + '</a>';
        }
      },
      {
        "width": "13%",
        "targets": 3,
        "data": "users",
        "render": function (data, type, full, meta) {
          result = '';
          for (var i = 0; i < data.length; i++) {
            result += '<a href="/fgases_registry/organisation_details?id='
            + full.company_id + '">' + data[i].username + '</a><br/>';
          }
          return result;
        }
      }
    ]
  });
}

function datatable_loading(action) {
  var target = $("#datatable");
  var t_parent = target.parent();
  var t_length = $("#datatable_length");
  var t_filter = $("#datatable_filter");
  var t_paginate = $("#datatable_paginate");
  var t_info = $("#datatable_info");
  var img_container = $(".spinner-container");
  if (img_container.length <= 0 ) {
    var img_container = $("<div />", {'class': 'spinner-container'});
    var img = $("<img />", {
                  'src': '++resource++static/ajax-loader.gif',
                  'class': 'ajax-spinner'
                });
    img_container.append(img);
    t_parent.prepend(img_container);
  }

  if (action === 'hide') {
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
}

function initDataTable() {
  /* Init the datatable object */

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
      "drawCallback": function (settings) {
        var api = this.api();
        var rows = api.rows({page: 'current'}).nodes();
        var last = null;

        api.column(2, {page:'current'}).data().each(function(group, i) {
          if (last !== group) {
            $(rows).eq(i).before(
              '<tr class="group"><td colspan="2">' + group + '</td></tr>'
            );
            last = group;
          }
        });
      },
      columnDefs: [
        {'visible': false, 'targets': 2}
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
  if (target.hasClass('bdr-datatable') && tableKey === 'by_path') {
    dtConfig.columns = [
      {"width": "25%"},
      {"width": "30%"},
      null
    ];
  }
  var dataTable = target.DataTable(dtConfig);
  $(".dataTables_filter input").attr('placeholder', 'Filter by...');
  var dataSources = {
    by_path: '/api.get_users_by_path',
    by_person: '/api.get_users'
  };

  datatable_loading('hide');
  // $('.placeholder', result).html(img);
  $.ajax({
    url: dataSources[tableKey],
    data: {
      obligation: $('#obligation').val(),
      role: $('#role').val(),
      countries: $('#countries').val()
    },
    success: function(result) {
      var rows = $.parseJSON(result).data;
      $.each(rows, function(idx, row) {
        dataTable.row.add(generateRow(row, tableKey));
      });
      datatable_loading('show');
      dataTable.draw();
    }
  });
}

function manage_role_cb(col_cb) {
  sel_roles = $(col_cb).parents('tr').find('.local-roles');
  if (sel_roles.length > 0) {
    sel_roles.prop('checked', $(col_cb).prop('checked'));
  }
}

$(function () {
  initEnvelopesTable();
  initCompaniesTable();

  $("#role, #obligation, #countries").select2({
    allowClear: true
  });

  if ($("#datatable").length !== 0)
    initDataTable();
  $(".toggledCB").click(function() {
    var checkedElems = $(".toggledCB").filter(function(index, element) {
      return $(element).prop('checked') === true;
    });
    if (checkedElems.length === $(".toggledCB").length) {
      $("#toggleAllCB").prop('checked', true);
    } else {
      $("#toggleAllCB").prop('checked', false);
    }
  });
  $(".toggledCB").change(function() {
      manage_role_cb(this);
  });
  $("#toggleAllCB").click(function() {
    var toggleAllBtn = $(this);
    var checkBoxes = $(".toggledCB");
    checkBoxes.prop('checked', toggleAllBtn.prop('checked'));
    $.each(checkBoxes, function(index, cb){
      manage_role_cb(cb);
    });
  });
});

function renderAsUL(li_items) {
  var result_html = '';

  $.each(li_items, function(index, li_item) {
    result_html += '<li>' + li_item + '</li>';
  });
  return '<ul>' + result_html + '</ul>';
}

function clear_filters() {
   $("#countries").select2("val", "");
   $("#obligation").select2("val", "");
   $("#role").select2("val", "");
}

function toggleSelectCountries(eu) {
  /* action can be select or deselect */
  var eu_keys = {'eu25': ['AT', 'BE', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES',
                          'FI', 'FR', 'GB', 'GR', 'HU', 'IE', 'IT', 'LT',
                          'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'SE', 'SI',
                          'SK'],
                 'eu27': ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES',
                          'FI','FR','GB','GR','HR', 'HU', 'IE', 'IT', 'LT',
                          'LU','LV','MT','NL', 'PL', 'PT', 'RO', 'SE', 'SI',
                          'SK'],
                 'eu31': ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES',
                          'FI', 'FR', 'GB', 'GR', 'HU', 'IE', 'IS', 'IT', 'LI',
                          'LT', 'LU', 'LV', 'MT', 'NO','NL', 'PL', 'PT', 'RO',
                          'SE', 'SI', 'SK', 'TR']};


  $("#s2id_countries").select2("val", eu_keys[eu]);
}

function renderAsLink(href, display, title) {
  var title_attribute = title ? ' title="' + title + '"' : '';
  return '<a href="' + href + '"' + title_attribute + '>' + display + '</a>';
}

function getUserUrl(user) {
  return 'http://www.eionet.europa.eu/directory/user?uid=' + user;
}
