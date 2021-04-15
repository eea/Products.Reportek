/*global $:false */
/*jslint browser:true */
"use strict";
var g_isSelected = false;

$(document).ready(function() {

  $("#selectAll").click(function () {
    if (!g_isSelected) {
      $("input:checkbox").prop('checked', true);
      $(this).val('Deselect all');
      $('#btn-xls-export-selected').attr('disabled', false);
      g_isSelected = true;
    } else {
      $("input:checkbox").prop('checked', false);
      $(this).val('Select all');
      $('#btn-xls-export-selected').attr('disabled', 'disabled');
      g_isSelected = false;
    }
  });

  $('#b_size').on('change', function() {
    var search_form = $('#frmSearch');
    var b_size = $(this).find(':selected').val();
    $('#batch_size').val(b_size);
    search_form.attr('action', '');
    search_form.submit();
  });

  $('.custom-search-btn').on('click', function(evt){
    evt.preventDefault();
    var search_form = $('#frmSearch');
    var action = $(this).attr('data-action');
    if ($(this).attr('id') === 'btn-xls-export') {
      var xls_max_rows = parseInt($(this).attr('data-xls_max_rows'), 10);
      var results_no = parseInt($(this).attr('data-results_no'), 10);
      if (results_no > xls_max_rows) {
        window.alert('XLS export is currently limited to ' + xls_max_rows + ' rows maximum!');
      }
    }
    search_form.attr('action', action);
    search_form.submit();
  });

  $('.custom-result-btn').on('click', function(evt){
    evt.preventDefault();
    var results_form = $('#results-form');
    var action = $(this).attr('data-action');
    results_form.attr('action', action);
    results_form.submit();
  });

  $('input[name="envelopes"]').on('change', function(){
      var checked = $('input[name="envelopes"]:checked');
      if (checked.length > 0) {
        $('#btn-xls-export-selected').attr('disabled', false);
      } else {
        $('#btn-xls-export-selected').attr('disabled', 'disabled');
      }
  });
});
