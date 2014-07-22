function initDataTables() {
    /* Init the datatable object */

    var target = $("#datatable_by_path, #datatable_by_person");
    if (!target.length)
        /* If is not the correct context get out from the the function */
        return;

    var tableSettings = {
        basic: {
            "serverSide": true,
            "pagingType": "simple",
            "pagining":true,
            "oLanguage":
            {
                "sInfo": "",
                "sInfoFiltered": "",
            },
        },
        by_path: {
            settings: {
                "columns": [
                    { "data": "path" },
                    { "data": "last_change" },
                    { "data": "obligations", "bSortable": false },
                    { "data": "users", "bSortable": false }
                ],
                "columnDefs":[
                    { "targets": 0,
                        "render": function(data, type, row) {
                        return '<a href="' + data[0] + '">' + data[1] + '</a>';}
                    },
                    {
                        "targets": 2,
                        "render": renderAsLI
                    },
                    {
                        "targets": 3,
                        "render": renderAsLI
                    }
                ],
                "fnServerParams": function(aoData) {
                    aoData.obligations = $('#obligations').val();
                    aoData.countries = $('#countries').val();
                    aoData.role = $('#role').val();
                }
            },
            ajax: '/data-source'
        },
        by_person: {
            settings: {
                "columns": [
                    { "data": "auditor" },
                    { "data": "path" }
                ]
            },
            ajax:'/data-person'
        }
    };

    var settings_name = target.get(0).getAttribute("data-tableSettings");
    var basic = tableSettings.basic;
    /* Set up the ajax's path */
    basic.ajax = tableSettings[settings_name].ajax;
    var settings = $.extend(basic, tableSettings[settings_name].settings);
    target.DataTable(settings);
}

$(function () {
    /*TODO: set up the correct context for the select2*/
    $("#obligations").select2({
        width: 200
    });
    $("#role").select2({
        width: 200
    });
    $("#countries").select2({
        width: 200
    });

    initDataTables();
});

function renderAsLI(data, type, row) {
    var result_html = '';
    $.each(data, function(index, value) {
        result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a></li>';
    });
    return '<ul>' + result_html + '</ul>';
}
