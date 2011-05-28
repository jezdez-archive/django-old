import datetime
import os
from decimal import Decimal
from django.test import TestCase
from django import forms
from django.core.exceptions import ValidationError
from modeltests.model_forms.models import (Article, Category, Writer,
    ImprovedArticle, WriterProfile, BetterWriter, Book, DerivedBook, Post,
    FlexibleDatePost, ImprovedArticleWithParentLink, PhoneNumber, TextFile,
    BigInt, Inventory, CustomFieldForExclusionModel, ArticleStatus, ImageFile,
    OptionalImageFile, CommaSeparatedInteger, Price)
from modeltests.model_forms.mforms import (ProductForm, PriceForm, BookForm,
    DerivedBookForm, ExplicitPKForm, PostForm, DerivedPostForm,
    CustomWriterForm, FlexDatePostForm)


class IncompleteCategoryFormWithFields(forms.ModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """
    url = forms.CharField(required=False)

    class Meta:
        fields = ('name', 'slug')
        model = Category

class IncompleteCategoryFormWithExclude(forms.ModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """
    url = forms.CharField(required=False)

    class Meta:
        exclude = ['url']
        model = Category


class ValidationTest(TestCase):
    def test_validates_with_replaced_field_not_specified(self):
        form = IncompleteCategoryFormWithFields(data={'name': 'some name', 'slug': 'some-slug'})
        assert form.is_valid()

    def test_validates_with_replaced_field_excluded(self):
        form = IncompleteCategoryFormWithExclude(data={'name': 'some name', 'slug': 'some-slug'})
        assert form.is_valid()

    def test_notrequired_overrides_notblank(self):
        form = CustomWriterForm({})
        assert form.is_valid()

# unique/unique_together validation
class UniqueTest(TestCase):
    def setUp(self):
        self.writer = Writer.objects.create(name='Mike Royko')

    def test_simple_unique(self):
        form = ProductForm({'slug': 'teddy-bear-blue'})
        self.assertTrue(form.is_valid())
        obj = form.save()
        form = ProductForm({'slug': 'teddy-bear-blue'})
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Product with this Slug already exists.'])
        form = ProductForm({'slug': 'teddy-bear-blue'}, instance=obj)
        self.assertTrue(form.is_valid())

    def test_unique_together(self):
        """ModelForm test of unique_together constraint"""
        form = PriceForm({'price': '6.00', 'quantity': '1'})
        self.assertTrue(form.is_valid())
        form.save()
        form = PriceForm({'price': '6.00', 'quantity': '1'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Price with this Price and Quantity already exists.'])

    def test_unique_null(self):
        title = 'I May Be Wrong But I Doubt It'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Book with this Title and Author already exists.'])
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())

    def test_inherited_unique(self):
        title = 'Boss'
        Book.objects.create(title=title, author=self.writer, special_id=1)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'special_id': u'1', 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['special_id'], [u'Book with this Special id already exists.'])

    def test_inherited_unique_together(self):
        title = 'Boss'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = DerivedBookForm({'title': title, 'author': self.writer.pk, 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Book with this Title and Author already exists.'])

    def test_abstract_inherited_unique(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'isbn': isbn})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['isbn'], [u'Derived book with this Isbn already exists.'])

    def test_abstract_inherited_unique_together(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'isbn': '9876', 'suffix1': u'0', 'suffix2': u'0'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Derived book with this Suffix1 and Suffix2 already exists.'])

    def test_explicitpk_unspecified(self):
        """Test for primary_key being in the form and failing validation."""
        form = ExplicitPKForm({'key': u'', 'desc': u'' })
        self.assertFalse(form.is_valid())

    def test_explicitpk_unique(self):
        """Ensure keys and blank character strings are tested for uniqueness."""
        form = ExplicitPKForm({'key': u'key1', 'desc': u''})
        self.assertTrue(form.is_valid())
        form.save()
        form = ExplicitPKForm({'key': u'key1', 'desc': u''})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)
        self.assertEqual(form.errors['__all__'], [u'Explicit pk with this Key and Desc already exists.'])
        self.assertEqual(form.errors['desc'], [u'Explicit pk with this Desc already exists.'])
        self.assertEqual(form.errors['key'], [u'Explicit pk with this Key already exists.'])

    def test_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], [u'Title must be unique for Posted date.'])
        form = PostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = PostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Slug must be unique for Posted year.'])
        form = PostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], [u'Subtitle must be unique for Posted month.'])
        form = PostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0", 'posted': '2008-09-03'}, instance=p)
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released"})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['posted'], [u'This field is required.'])

    def test_inherited_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], [u'Title must be unique for Posted date.'])
        form = DerivedPostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Slug must be unique for Posted year.'])
        form = DerivedPostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], [u'Subtitle must be unique for Posted month.'])
        form = DerivedPostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0", 'posted': '2008-09-03'}, instance=p)
        self.assertTrue(form.is_valid())

    def test_unique_for_date_with_nullable_date(self):
        p = FlexibleDatePost.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        form = FlexDatePostForm({'title': "Django 1.0 is released"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'slug': "Django 1.0"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'subtitle': "Finally"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0"}, instance=p)
        self.assertTrue(form.is_valid())


class _ANY(object):
    def __eq__(self, other):
        return True

ANY = _ANY()


class ModelFormsTests(TestCase):
    def tearDown(self):
        # Clean up
        from modeltests.model_forms.models import cleanup_storage
        cleanup_storage()

    def test_modelforms(self):
        from django import forms
        from django.forms.models import ModelForm, model_to_dict
        from django.core.files.uploadedfile import SimpleUploadedFile

        # The bare bones, absolutely nothing custom, basic case.

        class CategoryForm(ModelForm):
            class Meta:
                model = Category
        self.assertEqual(CategoryForm.base_fields.keys(), ['name', 'slug', 'url'])


        # Extra fields.

        class CategoryForm(ModelForm):
            some_extra_field = forms.BooleanField()

            class Meta:
                model = Category

        self.assertEqual(CategoryForm.base_fields.keys(), ['name', 'slug', 'url', 'some_extra_field'])

        # Extra field that has a name collision with a related object accessor.

        class WriterForm(ModelForm):
            book = forms.CharField(required=False)

            class Meta:
                model = Writer

        wf = WriterForm({'name': 'Richard Lockridge'})
        self.assertEqual(wf.is_valid(), True)

        # Replacing a field.

        class CategoryForm(ModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category

        self.assertEqual(CategoryForm.base_fields['url'].__class__, forms.BooleanField)


        # Using 'fields'.

        class CategoryForm(ModelForm):

            class Meta:
                model = Category
                fields = ['url']

        self.assertEqual(CategoryForm.base_fields.keys(), ['url'])


        # Using 'exclude'

        class CategoryForm(ModelForm):

            class Meta:
                model = Category
                exclude = ['url']

        self.assertEqual(CategoryForm.base_fields.keys(), ['name', 'slug'])


        # Using 'fields' *and* 'exclude'. Not sure why you'd want to do this, but uh,
        # "be liberal in what you accept" and all.

        class CategoryForm(ModelForm):

            class Meta:
                model = Category
                fields = ['name', 'url']
                exclude = ['url']

        self.assertEqual(CategoryForm.base_fields.keys(), ['name'])

        # Using 'widgets'

        class CategoryForm(ModelForm):

            class Meta:
                model = Category
                fields = ['name', 'url', 'slug']
                widgets = {
                    'name': forms.Textarea,
                    'url': forms.TextInput(attrs={'class': 'url'})
                }

        self.assertHTMLEqual(str(CategoryForm()['name']), '<textarea id="id_name" name="name" rows="10" cols="40"></textarea>\n')

        self.assertHTMLEqual(str(CategoryForm()['url']), '<input id="id_url" type="text" class="url" name="url" maxlength="40" />\n')

        self.assertHTMLEqual(str(CategoryForm()['slug']), '<input id="id_slug" type="text" name="slug" maxlength="20" />\n')

        # Don't allow more than one 'model' definition in the inheritance hierarchy.
        # Technically, it would generate a valid form, but the fact that the resulting
        # save method won't deal with multiple objects is likely to trip up people not
        # familiar with the mechanics.

        class CategoryForm(ModelForm):
            class Meta:
                model = Category

        class OddForm(CategoryForm):
            class Meta:
                model = Article

        # OddForm is now an Article-related thing, because BadForm.Meta overrides
        # CategoryForm.Meta.
        self.assertEqual(OddForm.base_fields.keys(), ['headline', 'slug', 'pub_date', 'writer', 'article', 'categories', 'status'])

        class ArticleForm(ModelForm):
            class Meta:
                model = Article

        # First class with a Meta class wins.

        class BadForm(ArticleForm, CategoryForm):
            pass
        self.assertEqual(OddForm.base_fields.keys(), ['headline', 'slug', 'pub_date', 'writer', 'article', 'categories', 'status'])

        # Subclassing without specifying a Meta on the class will use the parent's Meta
        # (or the first parent in the MRO if there are multiple parent classes).

        class CategoryForm(ModelForm):
            class Meta:
                model = Category
        class SubCategoryForm(CategoryForm):
            pass
        self.assertEqual(SubCategoryForm.base_fields.keys(), ['name', 'slug', 'url'])

        # We can also subclass the Meta inner class to change the fields list.

        class CategoryForm(ModelForm):
            checkbox = forms.BooleanField()

            class Meta:
                model = Category
        class SubCategoryForm(CategoryForm):
            class Meta(CategoryForm.Meta):
                exclude = ['url']

        self.assertHTMLEqual(unicode(SubCategoryForm()), '''
        <tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" />
        </td></tr>
        <tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" />
        </td></tr>
        <tr><th><label for="id_checkbox">Checkbox:</label></th><td><input type="checkbox" name="checkbox" id="id_checkbox" />
        </td></tr>
        ''')

        # test using fields to provide ordering to the fields
        class CategoryForm(ModelForm):
            class Meta:
                model = Category
                fields = ['url', 'name']

        self.assertEqual(CategoryForm.base_fields.keys(), ['url', 'name'])


        self.assertHTMLEqual(unicode(CategoryForm()), '''
        <tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" />
        </td></tr>
        <tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" />
        </td></tr>
        ''')

        class CategoryForm(ModelForm):
            class Meta:
                model = Category
                fields = ['slug', 'url', 'name']
                exclude = ['url']

        self.assertEqual(CategoryForm.base_fields.keys(), ['slug', 'name'])

        # Old form_for_x tests #######################################################

        from django.forms import ModelForm, CharField
        import datetime

        self.assertEqual(map(lambda o: o.name, Category.objects.all()), [])

        class CategoryForm(ModelForm):
            class Meta:
                model = Category
        f = CategoryForm()
        self.assertHTMLEqual(f, '''
        <tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" />
        </td></tr>
        <tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" />
        </td></tr>
        <tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" />
        </td></tr>
        ''')

        self.assertHTMLEqual(f.as_ul(), '''
        <li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="20" />
        </li>
        <li><label for="id_slug">Slug:</label> <input id="id_slug" type="text" name="slug" maxlength="20" />
        </li>
        <li><label for="id_url">The URL:</label> <input id="id_url" type="text" name="url" maxlength="40" />
        </li>
        ''')

        self.assertHTMLEqual(f['name'], '''
        <input type="text" name="name" id="id_name" maxlength="20" />
        ''')

        f = CategoryForm(auto_id=False)
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Name: <input type="text" name="name" maxlength="20" />
        </li>
        <li>Slug: <input type="text" name="slug" maxlength="20" />
        </li>
        <li>The URL: <input type="text" name="url" maxlength="40" />
        </li>
        ''')

        f = CategoryForm({'name': 'Entertainment', 'slug': 'entertainment', 'url': 'entertainment'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['url'], u'entertainment')
        self.assertEqual(f.cleaned_data['name'], u'Entertainment')
        self.assertEqual(f.cleaned_data['slug'], u'entertainment')
        c1 = f.save()
        self.assertEqual(c1.name, 'Entertainment')
        self.assertEqual(map(lambda o: o.name, Category.objects.all()), ["Entertainment"])

        f = CategoryForm({'name': "It's a test", 'slug': 'its-test', 'url': 'test'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['url'], u'test')
        self.assertEqual(f.cleaned_data['name'], u"It's a test")
        self.assertEqual(f.cleaned_data['slug'], u'its-test')
        c2 = f.save()
        self.assertEqual(c2.name, "It's a test")
        self.assertEqual(map(lambda o: o.name, Category.objects.order_by('name')), ["Entertainment", "It's a test"])

        # If you call save() with commit=False, then it will return an object that
        # hasn't yet been saved to the database. In this case, it's up to you to call
        # save() on the resulting model instance.
        f = CategoryForm({'name': 'Third test', 'slug': 'third-test', 'url': 'third'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['url'], u'third')
        self.assertEqual(f.cleaned_data['name'], u'Third test')
        self.assertEqual(f.cleaned_data['slug'], u'third-test')
        c3 = f.save(commit=False)
        self.assertEqual(c3.name, "Third test")
        self.assertEqual(map(lambda o: o.name, Category.objects.order_by('name')), ["Entertainment", "It's a test"])
        c3.save()
        self.assertEqual(map(lambda o: o.name, Category.objects.order_by('name')), ["Entertainment", "It's a test", "Third test"])

        # If you call save() with invalid data, you'll get a ValueError.
        f = CategoryForm({'name': '', 'slug': 'not a slug!', 'url': 'foo'})
        self.assertEqual(f.errors['name'], [u'This field is required.'])
        self.assertEqual(f.errors['slug'], [u"Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."])
        with self.assertRaises(AttributeError):
            f.cleaned_data
        with self.assertRaises(ValueError):
            f.save()
        f = CategoryForm({'name': '', 'slug': '', 'url': 'foo'})
        with self.assertRaises(ValueError):
            f.save()

        # Create a couple of Writers.
        w_royko = Writer(name='Mike Royko')
        w_royko.save()
        w_woodward = Writer(name='Bob Woodward')
        w_woodward.save()
        # ManyToManyFields are represented by a MultipleChoiceField, ForeignKeys and any
        # fields with the 'choices' attribute are represented by a ChoiceField.
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm(auto_id=False)
        self.assertHTMLEqual(f, '''
        <tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" />
        </td></tr>
        <tr><th>Slug:</th><td><input type="text" name="slug" maxlength="50" />
        </td></tr>
        <tr><th>Pub date:</th><td><input type="text" name="pub_date" />
        </td></tr>
        <tr><th>Writer:</th><td><select name="writer">
        <option value="" selected="selected">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="1">Mike Royko</option>
        </select>
        </td></tr>
        <tr><th>Article:</th><td><textarea name="article" rows="10" cols="40"></textarea>
        </td></tr>
        <tr><th>Categories:</th><td><select name="categories" multiple="multiple">
        <option value="1">Entertainment</option>
        <option value="2">It&#39;s a test</option>
        <option value="3">Third test</option>
        </select>
        <br /><span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></td></tr>
        <tr><th>Status:</th><td><select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </td></tr>
        ''')

        # You can restrict a form to a subset of the complete list of fields
        # by providing a 'fields' argument. If you try to save a
        # model created with such a form, you need to ensure that the fields
        # that are _not_ on the form have default values, or are allowed to have
        # a value of None. If a field isn't specified on a form, the object created
        # from the form can't provide a value for that field!
        class PartialArticleForm(ModelForm):
            class Meta:
                model = Article
                fields = ('headline','pub_date')
        f = PartialArticleForm(auto_id=False)
        self.assertHTMLEqual(f, '''
        <tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" />
        </td></tr>
        <tr><th>Pub date:</th><td><input type="text" name="pub_date" />
        </td></tr>
        ''')

        # When the ModelForm is passed an instance, that instance's current values are
        # inserted as 'initial' data in each Field.
        w = Writer.objects.get(name='Mike Royko')
        class RoykoForm(ModelForm):
            class Meta:
                model = Writer
        f = RoykoForm(auto_id=False, instance=w)
        self.assertHTMLEqual(f, '''
        <tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" />
        <br /><span class="helptext">Use both first and last names.</span></td></tr>
        ''')

        art = Article(headline='Test article', slug='test-article', pub_date=datetime.date(1988, 1, 4), writer=w, article='Hello.')
        art.save()
        art_id_1 = art.id
        self.assertEqual(art_id_1 is not None, True)
        class TestArticleForm(ModelForm):
            class Meta:
                model = Article
        f = TestArticleForm(auto_id=False, instance=art)
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" value="Test article" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" value="test-article" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" value="1988-01-04" />
        </li>
        <li>Writer: <select name="writer">
        <option value="">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="1" selected="selected">Mike Royko</option>
        </select>
        </li>
        <li>Article: <textarea name="article" rows="10" cols="40">Hello.</textarea>
        </li>
        <li>Categories: <select name="categories" multiple="multiple">
        <option value="1">Entertainment</option>
        <option value="2">It&#39;s a test</option>
        <option value="3">Third test</option>
        </select>
         <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
        <li>Status: <select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </li>
        ''')
        f = TestArticleForm({'headline': u'Test headline', 'slug': 'test-headline', 'pub_date': u'1984-02-06', 'writer': unicode(w_royko.pk), 'article': 'Hello.'}, instance=art)
        self.assertEqual(f.errors, {})
        self.assertEqual(f.is_valid(), True)
        test_art = f.save()
        self.assertEqual(test_art.id == art_id_1, True)
        test_art = Article.objects.get(id=art_id_1)
        self.assertEqual(test_art.headline, u'Test headline')
        # You can create a form over a subset of the available fields
        # by specifying a 'fields' argument to form_for_instance.
        class PartialArticleForm(ModelForm):
            class Meta:
                model = Article
                fields=('headline', 'slug', 'pub_date')
        f = PartialArticleForm({'headline': u'New headline', 'slug': 'new-headline', 'pub_date': u'1988-01-04'}, auto_id=False, instance=art)
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" value="1988-01-04" />
        </li>
        ''')
        self.assertEqual(f.is_valid(), True)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertEqual(new_art.headline, u'New headline')

        # Add some categories and test the many-to-many form output.
        self.assertEqual(map(lambda o: o.name, new_art.categories.all()), [])
        new_art.categories.add(Category.objects.get(name='Entertainment'))
        self.assertEqual(map(lambda o: o.name, new_art.categories.all()), ["Entertainment"])
        class TestArticleForm(ModelForm):
            class Meta:
                model = Article
        f = TestArticleForm(auto_id=False, instance=new_art)
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" value="1988-01-04" />
        </li>
        <li>Writer: <select name="writer">
        <option value="">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="1" selected="selected">Mike Royko</option>
        </select>
        </li>
        <li>Article: <textarea name="article" rows="10" cols="40">Hello.</textarea>
        </li>
        <li>Categories: <select name="categories" multiple="multiple">
        <option value="1" selected="selected">Entertainment</option>
        <option value="2">It&#39;s a test</option>
        <option value="3">Third test</option>
        </select>
         <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
        <li>Status: <select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </li>
        ''')

        # Initial values can be provided for model forms
        f = TestArticleForm(auto_id=False, initial={'headline': 'Your headline here', 'categories': [str(c1.id), str(c2.id)]})
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" value="Your headline here" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" />
        </li>
        <li>Writer: <select name="writer">
        <option value="" selected="selected">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="1">Mike Royko</option>
        </select>
        </li>
        <li>Article: <textarea name="article" rows="10" cols="40"></textarea>
        </li>
        <li>Categories: <select name="categories" multiple="multiple">
        <option value="1" selected="selected">Entertainment</option>
        <option value="2" selected="selected">It&#39;s a test</option>
        <option value="3">Third test</option>
        </select>
         <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
        <li>Status: <select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </li>
        ''')

        f = TestArticleForm({'headline': u'New headline', 'slug': u'new-headline', 'pub_date': u'1988-01-04',
            'writer': unicode(w_royko.pk), 'article': u'Hello.', 'categories': [unicode(c1.id), unicode(c2.id)]}, instance=new_art)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertEqual(map(lambda o: o.name, new_art.categories.order_by('name')), ["Entertainment", "It's a test"])

        # Now, submit form data with no categories. This deletes the existing categories.
        f = TestArticleForm({'headline': u'New headline', 'slug': u'new-headline', 'pub_date': u'1988-01-04',
            'writer': unicode(w_royko.pk), 'article': u'Hello.'}, instance=new_art)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertEqual(map(lambda o: o.name, new_art.categories.all()), [])

        # Create a new article, with categories, via the form.
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm({'headline': u'The walrus was Paul', 'slug': u'walrus-was-paul', 'pub_date': u'1967-11-01',
            'writer': unicode(w_royko.pk), 'article': u'Test.', 'categories': [unicode(c1.id), unicode(c2.id)]})
        new_art = f.save()
        art_id_2 = new_art.id
        self.assertEqual(art_id_2 not in (None, art_id_1), True)
        new_art = Article.objects.get(id=art_id_2)
        self.assertEqual(map(lambda o: o.name, new_art.categories.order_by('name')), ["Entertainment", "It's a test"])

        # Create a new article, with no categories, via the form.
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm({'headline': u'The walrus was Paul', 'slug': u'walrus-was-paul', 'pub_date': u'1967-11-01',
            'writer': unicode(w_royko.pk), 'article': u'Test.'})
        new_art = f.save()
        art_id_3 = new_art.id
        self.assertEqual(art_id_3 not in (None, art_id_1, art_id_2), True)
        new_art = Article.objects.get(id=art_id_3)
        self.assertEqual(map(lambda o: o.name, new_art.categories.all()), [])

        # Create a new article, with categories, via the form, but use commit=False.
        # The m2m data won't be saved until save_m2m() is invoked on the form.
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm({'headline': u'The walrus was Paul', 'slug': 'walrus-was-paul', 'pub_date': u'1967-11-01',
            'writer': unicode(w_royko.pk), 'article': u'Test.', 'categories': [unicode(c1.id), unicode(c2.id)]})
        new_art = f.save(commit=False)

        # Manually save the instance
        new_art.save()
        art_id_4 = new_art.id
        self.assertEqual(art_id_4 not in (None, art_id_1, art_id_2, art_id_3), True)

        # The instance doesn't have m2m data yet
        new_art = Article.objects.get(id=art_id_4)
        self.assertEqual(map(lambda o: o.name, new_art.categories.all()), [])

        # Save the m2m data on the form
        f.save_m2m()
        self.assertEqual(map(lambda o: o.name, new_art.categories.order_by('name')), ["Entertainment", "It's a test"])

        # Here, we define a custom ModelForm. Because it happens to have the same fields as
        # the Category model, we can just call the form's save() to apply its changes to an
        # existing Category instance.
        class ShortCategory(ModelForm):
            name = CharField(max_length=5)
            slug = CharField(max_length=5)
            url = CharField(max_length=3)
        cat = Category.objects.get(name='Third test')
        self.assertEqual(cat.name, "Third test")
        self.assertEqual(cat.id == c3.id, True)
        form = ShortCategory({'name': 'Third', 'slug': 'third', 'url': '3rd'}, instance=cat)
        self.assertEqual(form.save().name, 'Third')
        self.assertEqual(Category.objects.get(id=c3.id).name, 'Third')

        # Here, we demonstrate that choices for a ForeignKey ChoiceField are determined
        # at runtime, based on the data in the database when the form is displayed, not
        # the data in the database when the form is instantiated.
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm(auto_id=False)
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" />
        </li>
        <li>Writer: <select name="writer">
        <option value="" selected="selected">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="1">Mike Royko</option>
        </select>
        </li>
        <li>Article: <textarea name="article" rows="10" cols="40"></textarea>
        </li>
        <li>Categories: <select name="categories" multiple="multiple">
        <option value="1">Entertainment</option>
        <option value="2">It&#39;s a test</option>
        <option value="3">Third</option>
        </select>
         <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
        <li>Status: <select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </li>
        ''')

        c4 = Category.objects.create(name='Fourth', url='4th')
        self.assertEqual(c4.name, 'Fourth')
        self.assertEqual(Writer.objects.create(name='Carl Bernstein').name, 'Carl Bernstein')
        self.assertHTMLEqual(f.as_ul(), '''
        <li>Headline: <input type="text" name="headline" maxlength="50" />
        </li>
        <li>Slug: <input type="text" name="slug" maxlength="50" />
        </li>
        <li>Pub date: <input type="text" name="pub_date" />
        </li>
        <li>Writer: <select name="writer">
        <option value="" selected="selected">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="3">Carl Bernstein</option>
        <option value="1">Mike Royko</option>
        </select>
        </li>
        <li>Article: <textarea name="article" rows="10" cols="40"></textarea>
        </li>
        <li>Categories: <select name="categories" multiple="multiple">
        <option value="1">Entertainment</option>
        <option value="2">It&#39;s a test</option>
        <option value="3">Third</option>
        <option value="4">Fourth</option>
        </select>
         <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
        <li>Status: <select name="status">
        <option value="" selected="selected">---------</option>
        <option value="1">Draft</option>
        <option value="2">Pending</option>
        <option value="3">Live</option>
        </select>
        </li>
        ''')

        # ModelChoiceField ############################################################

        from django.forms import ModelChoiceField, ModelMultipleChoiceField

        f = ModelChoiceField(Category.objects.all())
        self.assertEqual(list(f.choices), [(u'', u'---------'), (ANY, u'Entertainment'), (ANY, u"It's a test"), (ANY, u'Third'), (ANY, u'Fourth')])
        with self.assertRaises(ValidationError):
            f.clean('')
        with self.assertRaises(ValidationError):
            f.clean(None)
        with self.assertRaises(ValidationError):
            f.clean(0)
        self.assertEqual(f.clean(c3.id).name, 'Third')
        self.assertEqual(f.clean(c2.id).name, "It's a test")

        # Add a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        c5 = Category.objects.create(name='Fifth', url='5th')
        self.assertEqual(c5.name, 'Fifth')
        self.assertEqual(f.clean(c5.id).name, 'Fifth')

        # Delete a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        Category.objects.get(url='5th').delete()
        with self.assertRaises(ValidationError):
            f.clean(c5.id)

        f = ModelChoiceField(Category.objects.filter(pk=c1.id), required=False)
        self.assertEqual(f.clean(''), None)
        f.clean('')
        self.assertEqual(f.clean(str(c1.id)).name, "Entertainment")
        with self.assertRaises(ValidationError):
            f.clean('100')

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name='Fourth')
        self.assertEqual(list(f.choices), [(u'', u'---------'), (ANY, u'Entertainment'), (ANY, u"It's a test"), (ANY, u'Third')])
        self.assertEqual(f.clean(c3.id).name, 'Third')
        with self.assertRaises(ValidationError):
            f.clean(c4.id)

        # check that we can safely iterate choices repeatedly
        gen_one = list(f.choices)
        gen_two = f.choices
        self.assertEqual(gen_one[2], (ANY, u"It's a test"))
        self.assertEqual(list(gen_two), [(u'', u'---------'), (ANY, u'Entertainment'), (ANY, u"It's a test"), (ANY, u'Third')])

        # check that we can override the label_from_instance method to print custom labels (#4620)
        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "category " + str(obj)
        self.assertEqual(list(f.choices), [(u'', u'---------'), (ANY, 'category Entertainment'), (ANY, "category It's a test"), (ANY, 'category Third'), (ANY, 'category Fourth')])

        # ModelMultipleChoiceField ####################################################

        f = ModelMultipleChoiceField(Category.objects.all())
        self.assertEqual(list(f.choices), [(ANY, u'Entertainment'), (ANY, u"It's a test"), (ANY, u'Third'), (ANY, u'Fourth')])
        with self.assertRaises(ValidationError):
            f.clean(None)
        with self.assertRaises(ValidationError):
            f.clean([])
        self.assertEqual(map(lambda o: o.name, f.clean([c1.id])), ["Entertainment"])
        self.assertEqual(map(lambda o: o.name, f.clean([c2.id])), ["It's a test"])
        self.assertEqual(map(lambda o: o.name, f.clean([str(c1.id)])), ["Entertainment"])
        self.assertEqual(map(lambda o: o.name, f.clean([str(c1.id), str(c2.id)])), ["Entertainment", "It's a test"])
        self.assertEqual(map(lambda o: o.name, f.clean([c1.id, str(c2.id)])), ["Entertainment", "It's a test"])
        self.assertEqual(map(lambda o: o.name, f.clean((c1.id, str(c2.id)))), ["Entertainment", "It's a test"])
        with self.assertRaises(ValidationError):
            f.clean(['100'])
        with self.assertRaises(ValidationError):
            f.clean('hello')
        with self.assertRaises(ValidationError):
            f.clean(['fail'])

        # Add a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        c6 = Category.objects.create(id=6, name='Sixth', url='6th')
        self.assertEqual(c6.name, 'Sixth')
        self.assertEqual(map(lambda o: o.name, f.clean([c6.id])), ["Sixth"])

        # Delete a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        Category.objects.get(url='6th').delete()
        with self.assertRaises(ValidationError):
            f.clean([c6.id])

        f = ModelMultipleChoiceField(Category.objects.all(), required=False)
        self.assertEqual(f.clean([]), [])
        self.assertEqual(f.clean(()), [])
        with self.assertRaises(ValidationError):
            f.clean(['10'])
        with self.assertRaises(ValidationError):
            f.clean([str(c3.id), '10'])
        with self.assertRaises(ValidationError):
            f.clean([str(c1.id), '10'])

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name='Fourth')
        self.assertEqual(list(f.choices), [(ANY, u'Entertainment'), (ANY, u"It's a test"), (ANY, u'Third')])
        self.assertEqual(map(lambda o: o.name, f.clean([c3.id])), ["Third"])
        with self.assertRaises(ValidationError):
            f.clean([c4.id])
        with self.assertRaises(ValidationError):
            f.clean([str(c3.id), str(c4.id)])

        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "multicategory " + str(obj)
        self.assertEqual(list(f.choices), [(ANY, 'multicategory Entertainment'), (ANY, "multicategory It's a test"), (ANY, 'multicategory Third'), (ANY, 'multicategory Fourth')])

        # OneToOneField ###############################################################

        class ImprovedArticleForm(ModelForm):
            class Meta:
                model = ImprovedArticle
        self.assertEqual(ImprovedArticleForm.base_fields.keys(), ['article'])

        class ImprovedArticleWithParentLinkForm(ModelForm):
            class Meta:
                model = ImprovedArticleWithParentLink
        self.assertEqual(ImprovedArticleWithParentLinkForm.base_fields.keys(), [])

        bw = BetterWriter(name=u'Joe Better', score=10)
        bw.save()
        self.assertEqual(sorted(model_to_dict(bw).keys()), ['id', 'name', 'score', 'writer_ptr'])

        class BetterWriterForm(ModelForm):
            class Meta:
                model = BetterWriter
        form = BetterWriterForm({'name': 'Some Name', 'score': 12})
        self.assertEqual(form.is_valid(), True)
        bw2 = form.save()
        bw2.delete()

        class WriterProfileForm(ModelForm):
            class Meta:
                model = WriterProfile
        form = WriterProfileForm()
        self.assertHTMLEqual(form.as_p(), '''
        <p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
        <option value="" selected="selected">---------</option>
        <option value="2">Bob Woodward</option>
        <option value="3">Carl Bernstein</option>
        <option value="4">Joe Better</option>
        <option value="1">Mike Royko</option>
        </select>
        </p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" />
        </p>
        ''')

        data = {
            'writer': unicode(w_woodward.pk),
            'age': u'65',
        }
        form = WriterProfileForm(data)
        instance = form.save()
        self.assertEqual(unicode(instance), 'Bob Woodward is 65')

        form = WriterProfileForm(instance=instance)
        self.assertHTMLEqual(form.as_p(), '''
        <p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
        <option value="">---------</option>
        <option value="2" selected="selected">Bob Woodward</option>
        <option value="3">Carl Bernstein</option>
        <option value="4">Joe Better</option>
        <option value="1">Mike Royko</option>
        </select>
        </p>
        <p><label for="id_age">Age:</label> <input type="text" name="age" value="65" id="id_age" />
        </p>
        ''')

        # PhoneNumberField ############################################################

        class PhoneNumberForm(ModelForm):
            class Meta:
                model = PhoneNumber
        f = PhoneNumberForm({'phone': '(312) 555-1212', 'description': 'Assistance'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['phone'], u'312-555-1212')
        self.assertEqual(f.cleaned_data['description'], u'Assistance')

        # FileField ###################################################################

        # File forms.

        class TextFileForm(ModelForm):
            class Meta:
                model = TextFile

        # Test conditions when files is either not given or empty.

        f = TextFileForm(data={'description': u'Assistance'})
        self.assertEqual(f.is_valid(), False)
        f = TextFileForm(data={'description': u'Assistance'}, files={})
        self.assertEqual(f.is_valid(), False)

        # Upload a file and ensure it all works as expected.

        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test1.txt', 'hello world')})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['file']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        instance.file.delete()
        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test1.txt', 'hello world')})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['file']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        # Check if the max_length attribute has been inherited from the model.
        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test-maxlength.txt', 'hello world')})
        self.assertEqual(f.is_valid(), False)

        # Edit an instance that already has the file defined in the model. This will not
        # save the file again, but leave it exactly as it is.

        f = TextFileForm(data={'description': u'Assistance'}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['file'].name, 'tests/test1.txt')
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()

        # Override the file by uploading a new one.

        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test2.txt', 'hello world')}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test2.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test2.txt', 'hello world')})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test2.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()

        instance.delete()

        # Test the non-required FileField
        f = TextFileForm(data={'description': u'Assistance'})
        f.fields['file'].required = False
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, '')

        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test3.txt', 'hello world')}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Instance can be edited w/out re-uploading the file and existing file should be preserved.

        f = TextFileForm(data={'description': u'New Description'}, instance=instance)
        f.fields['file'].required = False
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.description, u'New Description')
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        instance.delete()

        f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test3.txt', 'hello world')})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        instance.delete()

        # BigIntegerField ################################################################
        class BigIntForm(forms.ModelForm):
            class Meta:
                model = BigInt

        bif = BigIntForm({'biggie': '-9223372036854775808'})
        self.assertEqual(bif.is_valid(), True)
        bif = BigIntForm({'biggie': '-9223372036854775809'})
        self.assertEqual(bif.is_valid(), False)
        self.assertEqual(bif.errors, {'biggie': [u'Ensure this value is greater than or equal to -9223372036854775808.']})
        bif = BigIntForm({'biggie': '9223372036854775807'})
        self.assertEqual(bif.is_valid(), True)
        bif = BigIntForm({'biggie': '9223372036854775808'})
        self.assertEqual(bif.is_valid(), False)
        self.assertEqual(bif.errors, {'biggie': [u'Ensure this value is less than or equal to 9223372036854775807.']})


        # ImageField ###################################################################

        # ImageField and FileField are nearly identical, but they differ slighty when
        # it comes to validation. This specifically tests that #6302 is fixed for
        # both file fields and image fields.

        class ImageFileForm(ModelForm):
            class Meta:
                model = ImageFile

        image_data = open(os.path.join(os.path.dirname(__file__), "test.png"), 'rb').read()
        image_data2 = open(os.path.join(os.path.dirname(__file__), "test2.png"), 'rb').read()

        f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['image']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['image']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Edit an instance that already has the (required) image defined in the model. This will not
        # save the image again, but leave it exactly as it is.

        f = ImageFileForm(data={'description': u'Look, it changed'}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['image'].name, 'tests/test.png')
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.height, 16)
        self.assertEqual(instance.width, 16)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        # Override the file by uploading a new one.

        f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data2)}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test2.png')
        self.assertEqual(instance.height, 32)
        self.assertEqual(instance.width, 48)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        instance.delete()

        f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data2)})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test2.png')
        self.assertEqual(instance.height, 32)
        self.assertEqual(instance.width, 48)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        instance.delete()

        # Test the non-required ImageField

        class OptionalImageFileForm(ModelForm):
            class Meta:
                model = OptionalImageFile

        f = OptionalImageFileForm(data={'description': u'Test'})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, None)
        self.assertEqual(instance.width, None)
        self.assertEqual(instance.height, None)

        f = OptionalImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test3.png', image_data)}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test3.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Editing the instance without re-uploading the image should not affect the image or its width/height properties
        f = OptionalImageFileForm(data={'description': u'New Description'}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.description, u'New Description')
        self.assertEqual(instance.image.name, 'tests/test3.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Delete the current file since this is not done by Django.
        instance.image.delete()
        instance.delete()

        f = OptionalImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test4.png', image_data2)})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test4.png')
        self.assertEqual(instance.width, 48)
        self.assertEqual(instance.height, 32)
        instance.delete()
        # Test callable upload_to behavior that's dependent on the value of another field in the model
        f = ImageFileForm(data={'description': u'And a final one', 'path': 'foo'}, files={'image': SimpleUploadedFile('test4.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'foo/test4.png')
        instance.delete()

        # Media on a ModelForm ########################################################

        # Similar to a regular Form class you can define custom media to be used on
        # the ModelForm.

        class ModelFormWithMedia(ModelForm):
            class Media:
                js = ('/some/form/javascript',)
                css = {
                    'all': ('/some/form/css',)
                }
            class Meta:
                model = PhoneNumber
        f = ModelFormWithMedia()
        self.assertHTMLEqual(f.media, '''
        <link href="/some/form/css" type="text/css" media="all" rel="stylesheet" />
        <script type="text/javascript" src="/some/form/javascript"></script>
        ''')

        class CommaSeparatedIntegerForm(ModelForm):
           class Meta:
               model = CommaSeparatedInteger

        f = CommaSeparatedIntegerForm({'field': '1,2,3'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': u'1,2,3'})
        f = CommaSeparatedIntegerForm({'field': '1a,2'})
        self.assertEqual(f.errors, {'field': [u'Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': ',,,,'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': u',,,,'})
        f = CommaSeparatedIntegerForm({'field': '1.2'})
        self.assertEqual(f.errors, {'field': [u'Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': '1,a,2'})
        self.assertEqual(f.errors, {'field': [u'Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': '1,,2'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': u'1,,2'})
        f = CommaSeparatedIntegerForm({'field': '1'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': u'1'})

        # This Price instance generated by this form is not valid because the quantity
        # field is required, but the form is valid because the field is excluded from
        # the form. This is for backwards compatibility.

        class PriceForm(ModelForm):
            class Meta:
                model = Price
                exclude = ('quantity',)
        form = PriceForm({'price': '6.00'})
        self.assertEqual(form.is_valid(), True)
        price = form.save(commit=False)
        with self.assertRaises(ValidationError):
            price.full_clean()

        # The form should not validate fields that it doesn't contain even if they are
        # specified using 'fields', not 'exclude'.
            class Meta:
                model = Price
                fields = ('price',)
        form = PriceForm({'price': '6.00'})
        self.assertEqual(form.is_valid(), True)

        # The form should still have an instance of a model that is not complete and
        # not saved into a DB yet.

        self.assertEqual(form.instance.price, Decimal('6.00'))
        self.assertEqual(form.instance.quantity is None, True)
        self.assertEqual(form.instance.pk is None, True)

        # Choices on CharField and IntegerField
        class ArticleForm(ModelForm):
            class Meta:
                model = Article
        f = ArticleForm()
        with self.assertRaises(ValidationError):
            f.fields['status'].clean('42')

        class ArticleStatusForm(ModelForm):
            class Meta:
                model = ArticleStatus
        f = ArticleStatusForm()
        with self.assertRaises(ValidationError):
            f.fields['status'].clean('z')

        # Foreign keys which use to_field #############################################

        apple = Inventory.objects.create(barcode=86, name='Apple')
        pear = Inventory.objects.create(barcode=22, name='Pear')
        core = Inventory.objects.create(barcode=87, name='Core', parent=apple)

        field = ModelChoiceField(Inventory.objects.all(), to_field_name='barcode')
        self.assertEqual(tuple(field.choices), (
            (u'', u'---------'),
            (86, u'Apple'),
            (87, u'Core'),
            (22, u'Pear')))

        class InventoryForm(ModelForm):
            class Meta:
                model = Inventory
        form = InventoryForm(instance=core)
        self.assertHTMLEqual(form['parent'], '''
        <select name="parent" id="id_parent">
        <option value="">---------</option>
        <option value="86" selected="selected">Apple</option>
        <option value="87">Core</option>
        <option value="22">Pear</option>
        </select>
        ''')
        data = model_to_dict(core)
        data['parent'] = '22'
        form = InventoryForm(data=data, instance=core)
        core = form.save()
        self.assertEqual(core.parent.name, 'Pear')

        class CategoryForm(ModelForm):
            description = forms.CharField()
            class Meta:
                model = Category
                fields = ['description', 'url']

        self.assertEqual(CategoryForm.base_fields.keys(), ['description', 'url'])

        self.assertHTMLEqual(CategoryForm(), '''
        <tr><th><label for="id_description">Description:</label></th><td><input type="text" name="description" id="id_description" />
        </td></tr>
        <tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" />
        </td></tr>
        ''')
        # to_field_name should also work on ModelMultipleChoiceField ##################

        field = ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')
        self.assertEqual(tuple(field.choices), ((86, u'Apple'), (87, u'Core'), (22, u'Pear')))
        self.assertEqual(map(lambda o: o.name, field.clean([86])), ['Apple'])

        class SelectInventoryForm(forms.Form):
            items = ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')
        form = SelectInventoryForm({'items': [87, 22]})
        self.assertEqual(form.is_valid(), True)
        self.assertEqual(len(form.cleaned_data), 1)
        self.assertEqual(map(lambda o: o.name, form.cleaned_data['items']), ['Core', 'Pear'])

        # Model field that returns None to exclude itself with explicit fields ########

        class CustomFieldForExclusionForm(ModelForm):
            class Meta:
                model = CustomFieldForExclusionModel
                fields = ['name', 'markup']

        self.assertEqual(CustomFieldForExclusionForm.base_fields.keys(), ['name'])

        self.assertHTMLEqual(CustomFieldForExclusionForm(), '''
        <tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="10" />
        </td></tr>
        ''')
