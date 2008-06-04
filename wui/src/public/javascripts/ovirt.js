// ovirt-specific javascript functions are defined here


// helper functions for dialogs and action links


// returns an array of selected values for flexigrid checkboxes
function get_selected_checkboxes(obj_form)
{
  var selected_array = new Array()
  var selected_index = 0
  var checkboxes
  if (obj_form.grid_checkbox) {
    if (obj_form.grid_checkbox.length == undefined) {
      checkboxes = [obj_form.grid_checkbox]
    } else {
      checkboxes = obj_form.grid_checkbox
    }
    for(var i=0; i < checkboxes.length; i++){
    if(checkboxes[i].checked)
      {
        selected_array[selected_index]= checkboxes[i].value
        selected_index++
      }
    }
  }
  return selected_array
}


// make sure that at least one item is selected to continue
function validate_selected(selected_array, name)
{
  if (selected_array.length == 0) {
    alert("Please select at least one " + name + "  to continue")
    return false
  } else {
    return true
  }
}

function add_hosts(url)
{
    hosts= get_selected_checkboxes(document.addhosts_grid_form)
    if (validate_selected(hosts, "host")) {
      $.post(url,
             { resource_ids: hosts.toString() },
              function(data,status){ 
                jQuery(document).trigger('close.facebox');
                $("#hosts_grid").flexReload()
		if (data.alert) {
		  alert(data.alert);
                }
               }, 'json');
    }
}
function add_storage(url)
{
    storage= get_selected_checkboxes(document.addstorage_grid_form)
    if (validate_selected(storage, "storage pool")) {
      $.post(url,
             { resource_ids: storage.toString() },
              function(data,status){ 
                jQuery(document).trigger('close.facebox');
                $("#storage_grid").flexReload()
		if (data.alert) {
		  alert(data.alert);
                }
               }, 'json');
    }
}
// deal with ajax form response, filling in validation messages where required.
function ajax_validation(response, status)
{
  if (response.object) {
    $(".fieldWithErrors").removeClass("fieldWithErrors");
    $("div.errorExplanation").remove();
    if (!response.success) {
      for(i=0; i<response.errors.length; i++) { 
        var element = $("div.form_field:has(#"+response.object + "_" + response.errors[i][0]+")");
        if (element) {
          element.addClass("fieldWithErrors");
          for(j=0; j<response.errors[i][1].length; j++) { 
            element.append('<div class="errorExplanation">'+response.errors[i][1][j]+'</div>');
          }
        }
      }
    }
    if (response.alert) {
      alert(response.alert)
    }
  }
}

// callback actions for dialog submissions
function afterHwPool(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      // FIXME do we need to reload the tree here

      // this is for reloading the host/storage grid when 
      // adding hosts/storage to a new HW pool
      if (response.resource_type) {
        $('#' + response.resource_type + '_grid').flexReload()
      }
      // do we have HW pools grid?
      //$("#vmpools_grid").flexReload()
    }
}
function afterVmPool(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      $("#vmpools_grid").flexReload()
    }
}
function afterStoragePool(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      $("#storage_grid").flexReload()
    }
}
function afterPermission(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      $("#users_grid").flexReload()
    }
}
function afterVm(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      $("#vms_grid").flexReload()
    }
}

//selection detail refresh 
function refresh_summary(element_id, url, obj_id){
  $('#'+element_id+'').load(url, { id: obj_id})
}
function refresh_summary_static(element_id, content){
    $('#'+element_id+'').innerHTML = content
}

function storage_detail_empty(){
    refresh_summary_static('storage_selection', '<div class="selection_left"> \
    <div>Select a storage volume.</div> \
  </div>')
}



