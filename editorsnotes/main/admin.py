from models import Note, Reference, Term, Alias, TermAssignment
from django.contrib import admin

class ReferenceInline(admin.StackedInline):
    model = Reference
    extra = 1

class TermAssignmentInline(admin.StackedInline):
    model = TermAssignment
    extra = 3

class AliasInline(admin.StackedInline):
    model = Alias
    extra = 3

class NoteAdmin(admin.ModelAdmin):
    inlines = (ReferenceInline, TermAssignmentInline)
    def save_model(self, request, note, form, change):
        if change: # updating existing note
            note.last_updater = request.user
        else: # adding new note
            note.creator = request.user
        note.save()
    def save_formset(self, request, form, formset, change):
        term_assignments = formset.save(commit=False)
        for term_assignment in term_assignments:
            term_assignment.creator = request.user
            term_assignment.save()
        formset.save_m2m()
    class Media:
        js = ('http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js', 
              'wymeditor/jquery.wymeditor.pack.js',
              'wymeditor_init.js')

class TermAdmin(admin.ModelAdmin):
    inlines = (AliasInline,)
    def save_model(self, request, term, form, change):
        if not change: # adding new term
            term.creator = request.user
        term.save()

admin.site.register(Note, NoteAdmin)
admin.site.register(Term, TermAdmin)