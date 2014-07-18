function initDataTables(table_id) {
    /*Init the datatable object used in zpt/utilities/list_users.zpt
     */
    $(table_id).DataTable({
        "serverSide":true,
        "ajax":'/data-source',
        "columns":[
            { "data": "path" },
            { "data": "last_change" },
            { "data": "obl" },
            { "data": "clients" }
        ],
        "columnDefs":[{
            "targets": 0,
            "render": function(data, type, full, meta) {
                return '<a href="'+full.url_path+'">'+data+'</a>';
            }
        },
            {
                "targets": 2,
                "render": function(data, type, full, meta) {
                    return data.join("<br />");
                }
            }
        ],
        "fnServerParams":function(aoData) {
            aoData['obligations'] = $('#obligations').val();
            aoData['countries'] = $('#countries').val();
            aoData['role'] = $('#role').val();
        }
    });
}

$(function () {
    $("#obligations").select2({
        width: 200
    });
    $("#role").select2({
        width: 200
    });
    $("#countries").select2({
        width: 200
    });

    $(document).ready(function () {
        if (!$('#table_id').length)
            //if no #table_id -> no context for initDataTables
            return;
        initDataTables('#table_id');
    })
})
