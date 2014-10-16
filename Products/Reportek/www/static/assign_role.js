$(function () {
  $("#obligations").select2({width: 200});
  $("#role").select2({
    width: 200,
    placeholder: "(All)",
    allowClear: true
  });
  $("#countries, #obligations").select2({width: 200});
});
