EditorsNotes.utils = {};

EditorsNotes.utils.truncateChars = function (text, length) {
  var l = length || 100;
  return text.length < l ? text :
    text.substr(0, l/2) + ' ... ' + text.substr( -(l/2) );
}

EditorsNotes.utils.getPageProject = function () {
  var path = window.location.pathname
    , project_match = /^\/projects\/([^\/]+)/.exec(path)

  return project_match.length ? project_match[1] : null;
}

// REFACTOR && COMMENT
EditorsNotes.utils.baseAutocompleteOptions = {
  source: function(request, response, x) {
    var targetModel = this.element.attr('search-target') || this.element.data('search-target'),
      query = {'q': request.term};

    if (this.element.attr('search-project-id')) {
      query['project_id'] = this.element.attr('search-project-id');
    }

    switch (targetModel) {
      case 'topics':
        $.getJSON('/api/topics/', query, function(data) {
          response($.map(data, function(item, index) {
            var val = item.preferred_name;
            return { id: item.id, value: val, label: truncateChars(val), uri: item.uri };
          }));
        });
        break;

      case 'notes':
        $.getJSON('/api/notes/', query, function(data) {
          response($.map(data, function(item, index) {
            var val = item.title;
            return { id: item.id, value: val, label: truncateChars(val), uri: item.uri };
          }));
        })
        break;

      case 'documents':
        $.getJSON('/api/documents/', query, function(data) {
          response($.map(data, function(item, index) {
            var val = item.description;
            return { id: item.id, value: val, label: truncateChars(val), uri: item.uri };
          }));
        })
        break;
    }
  },
  minLength: 2,
  select: function(event, ui) {
    var $this = $(event.target);
    if (ui.item && !$this.hasClass('autocomplete-no-redirect')) {
      location.href = ui.item.uri;
    } else if (ui.item) {
      var selectedItem = $('<div style="position: absolute; left: -9999px">').html(ui.item.value).appendTo('body'),
        newWidth = selectedItem.innerWidth() + 5 ;

      newWidth = newWidth > 700 ? 700 : newWidth;

      if (!$this.data('originalWidth')) {
        $this.data({
          'originalWidth': $this.innerWidth(),
          'selectSibling': $this.siblings('select')
        });
      }
      selectedItem.remove();

      $this
        .attr('readonly', 'true')
        .css('width', newWidth + 5 + 'px')
        .blur();

      if ($this.data('selectSibling').length > 0) {
        $this.data('selectSibling').attr('disabled', 'disabled');
      }

      $('<input type="hidden">').attr({
        'name': 'autocomplete-model',
        'value': $this.attr('search-target')
      }).insertAfter($this);
      $('<input type="hidden">').attr({
        'name': 'autocomplete-id',
        'value': ui.item.id
      }).insertAfter($this);

      $('<i class="icon-remove-sign clear-search">')
        .css({
          'margin-left': '6px',
          'cursor': 'pointer'
        })
        .insertAfter($this)
        .click(function() {
          var $this = $(this),
            $searchBar = $this.prev('input.search-autocomplete');
          $searchBar
            .removeAttr('readonly')
            .css('width', $searchBar.data('originalWidth') + 'px')
            .val('')
            .siblings('input[type="hidden"][name^="autocomplete-"]').remove();
          if ($searchBar.data('selectSibling').length > 0) {
            $searchBar.data('selectSibling').removeAttr('disabled');
          }
          $this.remove();
        });
    }
  }
}
