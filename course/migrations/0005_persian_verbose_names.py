from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0004_coursecategory_icon'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='coursecategory',
            options={'verbose_name': 'دسته\u200cبندی دوره', 'verbose_name_plural': 'دسته\u200cبندی\u200cهای دوره'},
        ),
        migrations.AlterModelOptions(
            name='course',
            options={'verbose_name': 'دوره', 'verbose_name_plural': 'دوره\u200cها', 'permissions': [('publish_course', 'Can publish course'), ('view_own_course_sales', 'Can view own course sales'), ('view_own_course_commission', 'Can view own course commission'), ('view_teacher_sales_ranking', 'Can view teacher sales ranking'), ('view_all_courses', 'Can view all courses'), ('change_any_course', 'Can change any course'), ('view_own_courses', 'Can view own courses')]},
        ),
        migrations.AlterModelOptions(
            name='courseseason',
            options={'verbose_name': 'فصل دوره', 'verbose_name_plural': 'فصل\u200cهای دوره'},
        ),
        migrations.AlterModelOptions(
            name='coursesession',
            options={'verbose_name': 'جلسهٔ دوره', 'verbose_name_plural': 'جلسات دوره'},
        ),
        migrations.AlterModelOptions(
            name='coursesessionprogress',
            options={'verbose_name': 'پیشرفت جلسه', 'verbose_name_plural': 'پیشرفت جلسات'},
        ),
        migrations.AlterModelOptions(
            name='coursesessionwatch',
            options={'verbose_name': 'نوبت تماشای جلسه', 'verbose_name_plural': 'نوبت\u200cهای تماشای جلسات'},
        ),
        migrations.AlterModelOptions(
            name='coursesessionwatchevent',
            options={'verbose_name': 'رویداد تماشا', 'verbose_name_plural': 'رویدادهای تماشا'},
        ),
        migrations.AlterModelOptions(
            name='coursesessionwatchedrange',
            options={'verbose_name': 'بازهٔ دیده\u200cشده', 'verbose_name_plural': 'بازه\u200cهای دیده\u200cشده'},
        ),
        migrations.AlterModelOptions(
            name='coursesessionhomeworksubmission',
            options={'verbose_name': 'تمرین ارسالی', 'verbose_name_plural': 'تمرین\u200cهای ارسالی', 'permissions': [('review_homework_submission', 'Can review homework submission')]},
        ),
        migrations.AlterModelOptions(
            name='giftvideo',
            options={'verbose_name': 'ویدئوی هدیه', 'verbose_name_plural': 'ویدئوهای هدیه', 'ordering': ['order', '-created_at']},
        ),
    ]
