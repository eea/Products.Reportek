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
      ajax: '/api.get_users_by_path',
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
    result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a><a class="revoke-roles" href="revoke_roles?search_term='+value[1] + '&search_param=cn&btnFind=Search+users"><i class="icon-trash"></i></a></li>';
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

function toggleSelectCountries(group_elem) {
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

  var countries = $("#s2id_countries");
  var current_selection = countries.select2("val");

  var group = $(group_elem);
  var eu = eu_keys[group.attr('id')];
  var action = group.attr('action');
  var root_text = group.attr('text_root');

  if (action == 'select') {
    countries.select2("val", current_selection.concat(eu));
    group.text("Deselect " + root_text);
    group.attr("action", "deselect");
  } else if (action == 'deselect') {
    var not_eu = [];
    jQuery.grep(current_selection, function(el) {
      if (jQuery.inArray(el, eu) == -1) not_eu.push(el);
    });
    countries.select2("val", not_eu);
    group.text("Select " + root_text);
    group.attr("action", "select");
  }
}
