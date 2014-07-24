function toggleSelectRoles() {
  var selectAllCB = document.getElementById("selectAllCB");
  var elems = document.getElementsByName("ids:list");
  for (i = 0; i < elems.length; i++) {
    elems[i].checked = selectAllCB.checked;
  }
}
