function initDataTable() {
  /* Init the datatable object */

  var target = $("#datatable");

  var generalSettings = {
    by_path: {
      "columns": [
        { "data": "path" },
        { "data": "last_change" },
        { "data": "obligations", "bSortable": false },
        { "data": "users", "bSortable": false }
      ]
    },
    by_person: {
      "columns": [
        { "data": "user" },
        { "data": "paths" }
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
  dtConfig.settings = generalSettings[tableKey];
  var dataTable = target.DataTable(dtConfig);

  var dataSources = {
    by_path: '/api.get_users_by_path'
  };
  $.ajax({
    url: dataSources[tableKey],
    data: {
      obligations: $('#obligations').val(),
      role: $('#role').val(),
      countries: $('#countries').val()
    },
    success: function(result) {
      var rows = $.parseJSON(result).data;
      $.each(rows, function(idx, row) {
        dataTable.row.add([
          renderAsLink(row.path[0], row.path[0], row.path[1]),
          row.last_change,
          renderAsUL($.map(row.obligations, function(obligation) {
            return renderAsLink(obligation[0], obligation[1]);
          })),
          renderAsUL($.map(row.users, function(user) {
            return renderAsLink(getUserUrl(user), user)
          }))
        ]);
      });
      dataTable.draw();
    }
  });
}

$(function () {
  $("#role").select2({
    placeholder: "(All)",
    allowClear: true
  });
  $("#countries, #obligations").select2();
  initDataTable();
});

function renderClientColumn(data, type, row) {
  var result_html = '';
  $.each(data, function(index, value) {
    result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a><a class="revoke-roles" href="revoke_roles?search_term='+value[1] + '&search_param=cn&btnFind=Search+users"><i class="icon-trash"></i></a></li>';
  });
  return '<ul>' + result_html + '</ul>';
}

function renderAsUL(li_items) {
  var result_html = '';

  $.each(li_items, function(index, li_item) {
    result_html += '<li>' + li_item + '</li>';
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

function renderAsLink(href, display, title) {
  var title_attribute = title ? ' title="' + title + '"' : '';
  return '<a href="' + href + '"' + title_attribute + '>' + display + '</a>';
}

function getUserUrl(user) {
  return 'http://www.eionet.europa.eu/directory/user?uid=' + user;
}
