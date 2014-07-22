function initDataTables(table_id) {
    /*Init the datatable object used in zpt/utilities/list_users.zpt
     */
    $(table_id).DataTable({
        "serverSide": true,
        "ajax":'/data-source',
        "pagingType": "simple",
        "pagining":true,
        "columns": [
            { "data": "path" },
            { "data": "last_change" },
            { "data": "obligations", "bSortable": false },
            { "data": "users", "bSortable": false }
        ],
        "columnDefs":[{
            "targets": 0,
            "render": function(data, type, row) {
                return '<a href="' + data[0] + '">' + data[1] + '</a>';
            }
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
        },
        "oLanguage":
        {
            "sInfo": "",
            "sInfoFiltered": "",
        },
    });
}

$(function () {
    if ($('#table_id').length) {

        $("#obligations").select2({
            width: 200
        });
        $("#role").select2({
            width: 200
        });
        $("#countries").select2({
            width: 200
        });

        initDataTables('#table_id');
    }
});

function renderAsLI(data, type, row) {
    var result_html = '';
    $.each(data, function(index, value) {
        result_html += '<li><a href="' + value[0] + '">' + value[1] + '</a></li>';
    });
    return '<ul>' + result_html + '</ul>';
}
