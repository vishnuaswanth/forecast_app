# Generated manually for ConversationContextModel

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationContextModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active_report_type', models.CharField(blank=True, help_text="Current report type: 'forecast' or 'roster'", max_length=20, null=True)),
                ('current_month', models.IntegerField(blank=True, help_text='Report month (1-12)', null=True)),
                ('current_year', models.IntegerField(blank=True, help_text='Report year', null=True)),
                ('context_data', models.JSONField(default=dict, help_text='Full ConversationContext serialized as JSON')),
                ('turn_count', models.IntegerField(default=0, help_text='Number of conversation turns')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conversation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='context', to='chat_app.chatconversation')),
            ],
            options={
                'db_table': 'chat_conversation_contexts',
            },
        ),
        migrations.AddIndex(
            model_name='conversationcontextmodel',
            index=models.Index(fields=['conversation'], name='chat_conver_convers_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationcontextmodel',
            index=models.Index(fields=['updated_at'], name='chat_conver_updated_d4e5f6_idx'),
        ),
    ]
