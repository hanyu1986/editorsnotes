/*
 * Top level object for anything we do.
 *
 */
var EditorsNotes = {};


/*
 * Functions to be executed on every page load.
 *
 */
$(document).ready(function () {

  var utils = EditorsNotes.utils

  // Initialize timeago.
  $('time.timeago').timeago();

  // Initialize autocomplete for search input box.
  $('input.search-autocomplete')
  .keydown(function(event) {
    // If no autocomplete menu item is active, submit on ENTER.
    if (event.keyCode == $.ui.keyCode.ENTER) {
      if ($('#ui-active-menuitem').length == 0) {
        $('#searchform form').submit();
      }
    }
  })
  .autocomplete(utils.baseAutocompleteOptions);

});
