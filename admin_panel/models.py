from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from accounts.models import User, BankAccount


class AdminAction(models.Model):
    """
    AdminAction model for logging administrative actions.
    
    Provides audit trail for all administrative actions performed
    on user accounts and bank accounts by admin users.
    """
    
    ACTION_TYPES = [
        ('account_freeze', 'Account Freeze'),
        ('account_unfreeze', 'Account Unfreeze'),
        ('account_close', 'Account Close'),
        ('account_approve', 'Account Approve'),
        ('balance_adjustment', 'Balance Adjustment'),
        ('user_deactivate', 'User Deactivate'),
        ('user_activate', 'User Activate'),
        ('password_reset', 'Password Reset'),
        ('permission_change', 'Permission Change'),
    ]
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text="Type of administrative action performed"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the action was performed"
    )
    description = models.TextField(
        help_text="Detailed description of the action performed"
    )
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for performing this action"
    )
    
    # The admin user who performed the action
    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_actions_performed',
        help_text="Admin user who performed this action"
    )
    
    # The target user (if action is user-related)
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_actions_received',
        null=True,
        blank=True,
        help_text="User who was the target of this action"
    )
    
    # The target bank account (if action is account-related)
    target_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='admin_actions',
        null=True,
        blank=True,
        help_text="Bank account that was the target of this action"
    )
    
    # Additional data for the action (JSON field for flexibility)
    additional_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data related to the action"
    )
    
    class Meta:
        db_table = 'admin_actions'
        verbose_name = 'Admin Action'
        verbose_name_plural = 'Admin Actions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['admin_user', 'timestamp']),
            models.Index(fields=['target_user', 'timestamp']),
            models.Index(fields=['target_account', 'timestamp']),
        ]
    
    def clean(self):
        """Custom validation for the AdminAction model."""
        # Validate that admin user has admin privileges
        if self.admin_user and not (self.admin_user.is_staff or self.admin_user.is_superuser):
            raise ValidationError({
                'admin_user': 'Only staff or superuser accounts can perform admin actions.'
            })
        
        # Validate that at least one target is specified
        if not self.target_user and not self.target_account:
            raise ValidationError({
                'target_user': 'Either target_user or target_account must be specified.',
                'target_account': 'Either target_user or target_account must be specified.'
            })
        
        # Validate action type specific requirements
        account_related_actions = ['account_freeze', 'account_unfreeze', 'account_close', 'account_approve', 'balance_adjustment']
        user_related_actions = ['user_deactivate', 'user_activate', 'password_reset', 'permission_change']
        
        if self.action_type in account_related_actions and not self.target_account:
            raise ValidationError({
                'target_account': f'Action type "{self.action_type}" requires a target account.'
            })
        
        if self.action_type in user_related_actions and not self.target_user:
            raise ValidationError({
                'target_user': f'Action type "{self.action_type}" requires a target user.'
            })
        
        # Validate that target account belongs to target user if both are specified
        if self.target_user and self.target_account:
            if self.target_account.user != self.target_user:
                raise ValidationError({
                    'target_account': 'Target account must belong to the target user.'
                })
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_account_related(self):
        """Check if this action is related to a bank account."""
        account_actions = ['account_freeze', 'account_unfreeze', 'account_close', 'account_approve', 'balance_adjustment']
        return self.action_type in account_actions
    
    def is_user_related(self):
        """Check if this action is related to a user."""
        user_actions = ['user_deactivate', 'user_activate', 'password_reset', 'permission_change']
        return self.action_type in user_actions
    
    def get_target_display(self):
        """Get a display string for the target of this action."""
        if self.target_account:
            return f"Account {self.target_account.account_number} ({self.target_account.user.username})"
        elif self.target_user:
            return f"User {self.target_user.username}"
        return "Unknown target"
    
    def get_summary(self):
        """Get a summary of this admin action."""
        action_display = self.get_action_type_display()
        target_display = self.get_target_display()
        return f"{action_display} - {target_display}"
    
    @classmethod
    def log_account_freeze(cls, admin_user, target_account, reason=None):
        """Helper method to log account freeze action."""
        return cls.objects.create(
            action_type='account_freeze',
            admin_user=admin_user,
            target_account=target_account,
            target_user=target_account.user,
            description=f"Account {target_account.account_number} has been frozen.",
            reason=reason
        )
    
    @classmethod
    def log_account_unfreeze(cls, admin_user, target_account, reason=None):
        """Helper method to log account unfreeze action."""
        return cls.objects.create(
            action_type='account_unfreeze',
            admin_user=admin_user,
            target_account=target_account,
            target_user=target_account.user,
            description=f"Account {target_account.account_number} has been unfrozen.",
            reason=reason
        )
    
    @classmethod
    def log_account_close(cls, admin_user, target_account, reason=None):
        """Helper method to log account close action."""
        return cls.objects.create(
            action_type='account_close',
            admin_user=admin_user,
            target_account=target_account,
            target_user=target_account.user,
            description=f"Account {target_account.account_number} has been closed.",
            reason=reason
        )
    
    @classmethod
    def log_account_approve(cls, admin_user, target_account, reason=None):
        """Helper method to log account approval action."""
        return cls.objects.create(
            action_type='account_approve',
            admin_user=admin_user,
            target_account=target_account,
            target_user=target_account.user,
            description=f"Account {target_account.account_number} has been approved.",
            reason=reason
        )
    
    @classmethod
    def log_balance_adjustment(cls, admin_user, target_account, old_balance, new_balance, reason=None):
        """Helper method to log balance adjustment action."""
        return cls.objects.create(
            action_type='balance_adjustment',
            admin_user=admin_user,
            target_account=target_account,
            target_user=target_account.user,
            description=f"Balance adjusted for account {target_account.account_number} from ${old_balance} to ${new_balance}.",
            reason=reason,
            additional_data={
                'old_balance': str(old_balance),
                'new_balance': str(new_balance)
            }
        )
    
    @classmethod
    def log_user_deactivate(cls, admin_user, target_user, reason=None):
        """Helper method to log user deactivation action."""
        return cls.objects.create(
            action_type='user_deactivate',
            admin_user=admin_user,
            target_user=target_user,
            description=f"User {target_user.username} has been deactivated.",
            reason=reason
        )
    
    @classmethod
    def log_user_activate(cls, admin_user, target_user, reason=None):
        """Helper method to log user activation action."""
        return cls.objects.create(
            action_type='user_activate',
            admin_user=admin_user,
            target_user=target_user,
            description=f"User {target_user.username} has been activated.",
            reason=reason
        )
    
    def __str__(self):
        return f"{self.get_action_type_display()} by {self.admin_user.username} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
