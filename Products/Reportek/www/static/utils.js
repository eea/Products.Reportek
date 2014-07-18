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
            debugger;
            aoData['obligations'] = $('#obligations').val();
            aoData['countries'] = $('#countries').val();
            aoData['role'] = $('#role').val();
        }
    });
}

$(function () {
    debugger;
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
})
