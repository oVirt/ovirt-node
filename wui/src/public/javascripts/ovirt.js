// ovirt-specific javascript functions are defined here


// helper functions for dialogs and action links


// returns an array of selected values for flexigrid checkboxes
function get_selected_checkboxes(formid)
{
  var selected_array = new Array()
  var selected_index = 0
  var selected = $('#'+formid+' .grid_checkbox:checkbox:checked')
  selected.each(function(){
    selected_array.push(this.value)  
  })
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
    hosts= get_selected_checkboxes("addhosts_grid_form")
    if (validate_selected(hosts, "host")) {
      $.post(url,
             { resource_ids: hosts.toString() },
              function(data,status){ 
                jQuery(document).trigger('close.facebox');
	        grid = $("#hosts_grid")
                if (grid.size()>0) {
                  grid.flexReload()
                } else {
		  $('.tab_nav li.current a').click()
                }
		if (data.alert) {
		  alert(data.alert);
                }
               }, 'json');
    }
}
function add_storage(url)
{
    storage= get_selected_checkboxes("addstorage_grid_form")
    if (validate_selected(storage, "storage pool")) {
      $.post(url,
             { resource_ids: storage.toString() },
              function(data,status){ 
                jQuery(document).trigger('close.facebox');
	        grid = $("#storage_grid")
                if (grid.size()>0) {
                  grid.flexReload()
                } else {
		  $('.tab_nav li.current a').click()
                }
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
      
      if ((response.resource_type == 'hosts' ? get_selected_hosts() : get_selected_storage()).indexOf($('#'+response.resource_type+'_selection_id').html()) != -1){
	  empty_summary(response.resource_type +'_selection', (response.resource_type == 'hosts' ? 'Host' : 'Storage Pool'))
      }   
      // do we have HW pools grid?
      //$("#vmpools_grid").flexReload()
    }
}
function afterVmPool(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      grid = $("#vmpools_grid")
      if (grid.size()>0) {
        grid.flexReload()
      } else {
        $('.tab_nav li.current a').click()
      }
    }
}
function afterStoragePool(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      grid = $("#storage_grid")
      if (grid.size()>0) {
        grid.flexReload()
      } else {
        $('.tab_nav li.current a').click()
      }
    }
}
function afterPermission(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      grid = $("#users_grid")
      if (grid.size()>0) {
        grid.flexReload()
      } else {
        $('.tab_nav li.current a').click()
      }
    }
}
function afterVm(response, status){
    ajax_validation(response, status)
    if (response.success) {
      jQuery(document).trigger('close.facebox');
      grid = $("#vms_grid")
      if (grid.size()>0) {
        grid.flexReload()
      } else {
        $('.tab_nav li.current a').click()
      }
    }
}

//selection detail refresh 
function refresh_summary(element_id, url, obj_id){
  $('#'+element_id+'').load(url, { id: obj_id})
}
function refresh_summary_static(element_id, content){
    $('#'+element_id+'').html(content)
}
function empty_summary(element_id, label){
    refresh_summary_static(element_id, '<div class="selection_left"> \
    <div>Select a '+label+' above.</div> \
  </div>')
}


function get_selected_storage()
{
    return get_selected_checkboxes("storage_grid_form");
}
function validate_storage_for_move()
{
    if (validate_selected(get_selected_storage(), 'storage pool')) {
        $('#move_link_hidden').click();
    }
}
function validate_storage_for_remove()
{
    if (validate_selected(get_selected_storage(), 'storage pool')) {
        $('#remove_link_hidden').click();
    }
}
function delete_or_remove_storage()
{
    var selected = $('#remove_storage_selection :radio:checked');
    if (selected[0].value == "remove") {
        remove_storage();
    } else if (selected[0].value == "delete") {
        delete_storage();
    }
    jQuery(document).trigger('close.facebox');
}


