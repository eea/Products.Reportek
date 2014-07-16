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
            return '<a href="'+full.url+'">'+data+'</a>';
            }
        } ]
    });
}
