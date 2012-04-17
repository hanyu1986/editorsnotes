$(document).ready(function() {

  var facets = [ 'year', 'itemtype' ];

  function select_document_filters(facet_name) {
    var filters = [];
    $('#document-' + facet_name + '-facet input:checked').each(function(index) {
      filters.push($(this).data('filter'));
    });
    return $('#document-list').find(filters.join(',')).map(function() {
      return ':has(#' + this.id + ')';
    }).get();
  }

  function update_filter() {
    var selected = [];
    $.each(facets, function(index, value) {
      selected.push(select_document_filters(value));
    });
    var intersection = _.intersect.apply(this, selected);
    var filter = (intersection.length == 0 ? '.nothing' : intersection.join(','));
    $('#document-list').isotope({ filter: filter });
  }

  function update_sort(facet_name, ascending) {
    $('#document-list').isotope({ 
      sortBy: facet_name,
      sortAscending: ascending
    });
  }

  function init_facet(name) {
    var keys = [];
    var counts = {};
    $('#document-list .document').each(function(index) {
      var value = $(this).data(name);
      if (value == undefined) {
        value = 'None';
      }
      if (value in counts) {
        counts[value] += 1;
      } else {
        if (value != 'None') {
          keys.push(value);
        }
        counts[value] = 1;
      }
    });
    keys.sort();
    if ('None' in counts) {
      keys.push('None');
    }
    $.each(keys, function(index, value) {
      $('<li><label class="checkbox"><input type="checkbox" checked/>' 
        + value + ' (' + counts[value] + ')</label></li>')
        .appendTo('#document-' + name + '-facet')
        .find(':checkbox')
        .data('filter', ((value == 'None') ? 
                         'div.document:not(div[data-' + name + '])' :
                         'div.document[data-' + name + '="' + value + '"]'))
        .change(function() { update_filter(); });
    });
    $('#' + name + '-select-all').change(function(event) {
      var value = $(this).attr('checked');
      $('#document-' + name + '-facet :checkbox').each(function() {
        $(this).attr('checked', value);
      });
      update_filter();
    });
  }

  function init_sort_buttons() {
    $('.sort-button').click(function() {
      if ($(this).hasClass('ui-state-default')) {
        $('.sort-button').removeClass('ui-state-highlight').addClass('ui-state-default');
        $(this).removeClass('ui-state-default').addClass('ui-state-highlight');
      } else { // ui-state-highlight
        $(this).find('.ui-icon')
          .toggleClass('ui-icon-triangle-1-s')
          .toggleClass('ui-icon-triangle-1-n');
      }
      var ascending = $(this).find('.ui-icon').hasClass('ui-icon-triangle-1-s');
      update_sort($(this).data('facet'), ascending);
    }).hover(function() {
      $(this).toggleClass('ui-state-hover');
    });
  }

  var isotope_ready = false;
  function init_isotope() {
    if (! isotope_ready) {
      var sort_functions = {};
      $.each(facets, function(index, value) {
        init_facet(value);
        sort_functions[value] = function(element) {
          var sortkey = element.find('.document').data(value);
          if (sortkey == undefined) { sortkey = 'zzzzzzzzzzzzzzzzzzzzzzzzz'; }
          return sortkey;
        };
      });
      $('#document-list').isotope({
        itemSelector: '.document-item',
        layoutMode: 'straightDown',
        getSortData: sort_functions
      });
      init_sort_buttons();
      $('#year-sort-button').click();
      isotope_ready = true;
    } 
  }

  // If no hash is present in URL, load default tab into history
  var url = $.param.fragment();
  if ( url == '' ) {
    window.location.replace(window.location.href + '#article');
    url = $.param.fragment();
  }

  var tabs = $('#tabs a');

  tabs.click(function(e) {
    e.preventDefault();
    var index = $(this).attr('href').match(/#(.+)-tab/)[1];
    $.bbq.pushState(index, 2);
  }).on('shown', function(e) {
    var targetPanel = e.target.hash;
    if (targetPanel.match(/documents/)) {
      init_isotope();
    }
  });

  $(window).bind('hashchange', function(e) {
    var index = $.bbq.getState();
    $.each(index, function(key, value) {
      var tabToOpen = tabs.filter('a[href*="' + key + '"]');
      if ( tabToOpen.length > 0 ) {
        tabToOpen.tab('show');
      }
    });
  }).trigger('hashchange');
});
