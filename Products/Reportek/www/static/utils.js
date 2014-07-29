function initDataTables() {
  /* Init the datatable object */

  var target = $("#datatable_by_path, #datatable_by_person");
  if (!target.length)
  /* If is not the correct context get out from the the function */
    return;

  var tableSettings = {
    basic: {
      "pagingType": "simple",
      "pagining":true,
      "oLanguage":
      {
        "sInfo": "",
        "sInfoFiltered": ""
      }
    },
    by_path: {
      settings: {
        "columns": [
          { "data": "path" },
          { "data": "last_change" },
          { "data": "obligations", "bSortable": false },
          { "data": "users", "bSortable": false }
        ],
        "columnDefs": [
          { "targets": 0,
            "render": function(data, type, row) {
              return '<a href="' + data[0] + '" title="' + data[2] + '" >' + data[1] + '</a>';
            }
          },
          {
            "targets": 2,
            "render": renderAsLI
          },
          {
            "targets": 3,
            "render": renderClientColumn
          }
        ],
        "fnServerParams": function(aoData) {
          aoData.obligations = $('#obligations').val();
          aoData.countries = $('#countries').val();
          aoData.role = $('#role').val();
        }
      },
      ajax: '/data-source',
      "serverSide": true
    },
    by_person: {
      settings: {
        "columns": [
          { "data": "user" },
          { "data": "paths" }
        ],
        "columnDefs": [
          {
            "targets": 1,
            "render": renderAsLI
          }
        ]
      },
      ajax:'/data-person',
      serverSide: false
    }
  };

  var settings_name = target.get(0).getAttribute("data-tableSettings");
  var basic = tableSettings.basic;
  /* Set up the ajax's path */
  basic.ajax = tableSettings[settings_name].ajax;
  basic.serverSide = tableSettings[settings_name].serverSide;
  var settings = $.extend(basic, tableSettings[settings_name].settings);
  target.DataTable(settings);
}

$(function () {
  $("#role").select2({
    placeholder: "(All)",
    allowClear: true
  });
  $("#countries, #obligations").select2();
  initDataTables();
});

function renderClientColumn(data, type, row) {
  var result_html = '';
  $.each(data, function(index, value) {
    result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a><a href="revoke_roles?search_term='+value[1] + '&search_param=cn&btnFind=Search+users">(x)</a></li>';
  });
  return '<ul>' + result_html + '</ul>';
}

function renderAsLI(data, type, row) {
  var result_html = '';
  $.each(data, function(index, value) {
    result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a></li>';
  });
  return '<ul>' + result_html + '</ul>';
}
