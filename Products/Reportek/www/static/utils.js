function initDataTables(table_id) {
    /*Init the datatable object used in zpt/utilities/list_users.zpt
     */
    $(table_id).DataTable({
        "serverSide": true,
        "ajax":'/data-source',
        "columns": [
            { "data": "short_path" },
            { "data": "last_change" },
            { "data": "obligations", "bSortable": false },
            { "data": "users", "bSortable": false }
        ],
        "columnDefs":[{
            "targets": 0,
            "render": function(data, type, row) {
                return '<a href="' + row.full_path + '">' + data + '</a>';
            }
        },
        {
            "targets": 2,
            "render": function(data, type, row) {
                return data.join("<br />");
            }
        }
        ],
        "fnServerParams": function(aoData) {
            aoData['obligations'] = $('#obligations').val();
            aoData['countries'] = $('#countries').val();
            aoData['role'] = $('#role').val();
        }
    });
}

$(function () {
    if ($('#table_id').length != 0) {

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
})
