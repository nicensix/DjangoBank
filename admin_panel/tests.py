from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from accounts.models import BankAccount
from .models import AdminAction

User = get_user_model()


class AdminActionModelTest(TestCase):
    """Test cases for the AdminAction model."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='superpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123'
        )
        self.target_user = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='targetpass123'
        )
        
        # Create test bank account
        self.target_account = BankAccount.objects.create(
            user=self.target_user,
            account_type='savings',
            balance=1000.00,
            status='active'
        )
    
    def test_create_account_freeze_action(self):
        """Test creating an account freeze admin action."""
        action = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Account frozen due to suspicious activity',
            reason='Suspicious transactions detected'
        )
        
        self.assertEqual(action.action_type, 'account_freeze')
        self.assertEqual(action.admin_user, self.admin_user)
        self.assertEqual(action.target_account, self.target_account)
        self.assertEqual(action.target_user, self.target_user)
        self.assertEqual(action.description, 'Account frozen due to suspicious activity')
        self.assertEqual(action.reason, 'Suspicious transactions detected')
        self.assertIsNotNone(action.timestamp)
    
    def test_create_user_deactivate_action(self):
        """Test creating a user deactivation admin action."""
        action = AdminAction.objects.create(
            action_type='user_deactivate',
            admin_user=self.superuser,
            target_user=self.target_user,
            description='User account deactivated',
            reason='Policy violation'
        )
        
        self.assertEqual(action.action_type, 'user_deactivate')
        self.assertEqual(action.admin_user, self.superuser)
        self.assertEqual(action.target_user, self.target_user)
        self.assertIsNone(action.target_account)
        self.assertEqual(action.description, 'User account deactivated')
        self.assertEqual(action.reason, 'Policy violation')
    
    def test_admin_user_validation(self):
        """Test that only staff or superuser can perform admin actions."""
        # Valid admin action with staff user
        action = AdminAction(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Test action'
        )
        action.full_clean()  # Should not raise
        
        # Valid admin action with superuser
        action = AdminAction(
            action_type='account_freeze',
            admin_user=self.superuser,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Test action'
        )
        action.full_clean()  # Should not raise
        
        # Invalid admin action with regular user
        action = AdminAction(
            action_type='account_freeze',
            admin_user=self.regular_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Test action'
        )
        with self.assertRaises(ValidationError) as context:
            action.full_clean()
        self.assertIn('admin_user', context.exception.message_dict)
        self.assertIn('staff or superuser', str(context.exception.message_dict['admin_user']))
    
    def test_target_validation(self):
        """Test that at least one target must be specified."""
        # Invalid action with no targets
        action = AdminAction(
            action_type='account_freeze',
            admin_user=self.admin_user,
            description='Test action'
        )
        with self.assertRaises(ValidationError) as context:
            action.full_clean()
        self.assertIn('target_user', context.exception.message_dict)
        self.assertIn('target_account', context.exception.message_dict)
    
    def test_account_related_action_validation(self):
        """Test validation for account-related actions."""
        account_actions = ['account_freeze', 'account_unfreeze', 'account_close', 'account_approve', 'balance_adjustment']
        
        for action_type in account_actions:
            # Valid action with target account
            action = AdminAction(
                action_type=action_type,
                admin_user=self.admin_user,
                target_account=self.target_account,
                target_user=self.target_user,
                description='Test action'
            )
            action.full_clean()  # Should not raise
            
            # Invalid action without target account
            action = AdminAction(
                action_type=action_type,
                admin_user=self.admin_user,
                target_user=self.target_user,
                description='Test action'
            )
            with self.assertRaises(ValidationError) as context:
                action.full_clean()
            self.assertIn('target_account', context.exception.message_dict)
    
    def test_user_related_action_validation(self):
        """Test validation for user-related actions."""
        user_actions = ['user_deactivate', 'user_activate', 'password_reset', 'permission_change']
        
        for action_type in user_actions:
            # Valid action with target user
            action = AdminAction(
                action_type=action_type,
                admin_user=self.admin_user,
                target_user=self.target_user,
                description='Test action'
            )
            action.full_clean()  # Should not raise
            
            # Invalid action without target user
            action = AdminAction(
                action_type=action_type,
                admin_user=self.admin_user,
                target_account=self.target_account,
                description='Test action'
            )
            with self.assertRaises(ValidationError) as context:
                action.full_clean()
            self.assertIn('target_user', context.exception.message_dict)
    
    def test_target_account_user_relationship_validation(self):
        """Test that target account must belong to target user."""
        # Create another user and account
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='otherpass123'
        )
        other_account = BankAccount.objects.create(
            user=other_user,
            account_type='current',
            balance=500.00,
            status='active'
        )
        
        # Invalid action - account doesn't belong to user
        action = AdminAction(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=other_account,
            target_user=self.target_user,  # Different user
            description='Test action'
        )
        with self.assertRaises(ValidationError) as context:
            action.full_clean()
        self.assertIn('target_account', context.exception.message_dict)
        self.assertIn('belong to the target user', str(context.exception.message_dict['target_account']))
    
    def test_action_type_methods(self):
        """Test action type checking methods."""
        account_action = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Account freeze action'
        )
        
        user_action = AdminAction.objects.create(
            action_type='user_deactivate',
            admin_user=self.admin_user,
            target_user=self.target_user,
            description='User deactivate action'
        )
        
        # Test account-related action
        self.assertTrue(account_action.is_account_related())
        self.assertFalse(account_action.is_user_related())
        
        # Test user-related action
        self.assertFalse(user_action.is_account_related())
        self.assertTrue(user_action.is_user_related())
    
    def test_get_target_display(self):
        """Test get_target_display method."""
        account_action = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Account freeze action'
        )
        
        user_action = AdminAction.objects.create(
            action_type='user_deactivate',
            admin_user=self.admin_user,
            target_user=self.target_user,
            description='User deactivate action'
        )
        
        # Test account action display
        account_display = account_action.get_target_display()
        self.assertIn(self.target_account.account_number, account_display)
        self.assertIn(self.target_user.username, account_display)
        
        # Test user action display
        user_display = user_action.get_target_display()
        self.assertIn(self.target_user.username, user_display)
    
    def test_get_summary(self):
        """Test get_summary method."""
        action = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Account freeze action'
        )
        
        summary = action.get_summary()
        self.assertIn('Account Freeze', summary)
        self.assertIn(self.target_account.account_number, summary)
        self.assertIn(self.target_user.username, summary)
    
    def test_helper_methods(self):
        """Test helper class methods for logging actions."""
        # Test account freeze logging
        freeze_action = AdminAction.log_account_freeze(
            admin_user=self.admin_user,
            target_account=self.target_account,
            reason='Suspicious activity'
        )
        self.assertEqual(freeze_action.action_type, 'account_freeze')
        self.assertEqual(freeze_action.admin_user, self.admin_user)
        self.assertEqual(freeze_action.target_account, self.target_account)
        self.assertEqual(freeze_action.reason, 'Suspicious activity')
        
        # Test account unfreeze logging
        unfreeze_action = AdminAction.log_account_unfreeze(
            admin_user=self.admin_user,
            target_account=self.target_account,
            reason='Issue resolved'
        )
        self.assertEqual(unfreeze_action.action_type, 'account_unfreeze')
        
        # Test balance adjustment logging
        balance_action = AdminAction.log_balance_adjustment(
            admin_user=self.admin_user,
            target_account=self.target_account,
            old_balance=Decimal('1000.00'),
            new_balance=Decimal('1500.00'),
            reason='Correction'
        )
        self.assertEqual(balance_action.action_type, 'balance_adjustment')
        self.assertEqual(balance_action.additional_data['old_balance'], '1000.00')
        self.assertEqual(balance_action.additional_data['new_balance'], '1500.00')
        
        # Test user deactivation logging
        deactivate_action = AdminAction.log_user_deactivate(
            admin_user=self.admin_user,
            target_user=self.target_user,
            reason='Policy violation'
        )
        self.assertEqual(deactivate_action.action_type, 'user_deactivate')
        self.assertEqual(deactivate_action.target_user, self.target_user)
    
    def test_additional_data_field(self):
        """Test the additional_data JSON field."""
        action = AdminAction.objects.create(
            action_type='balance_adjustment',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Balance adjustment',
            additional_data={
                'old_balance': '1000.00',
                'new_balance': '1200.00',
                'adjustment_type': 'credit'
            }
        )
        
        self.assertEqual(action.additional_data['old_balance'], '1000.00')
        self.assertEqual(action.additional_data['new_balance'], '1200.00')
        self.assertEqual(action.additional_data['adjustment_type'], 'credit')
    
    def test_string_representation(self):
        """Test the string representation of admin actions."""
        action = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='Account freeze action'
        )
        
        str_repr = str(action)
        self.assertIn('Account Freeze', str_repr)
        self.assertIn(self.admin_user.username, str_repr)
        self.assertIn(action.timestamp.strftime('%Y-%m-%d'), str_repr)
    
    def test_model_relationships(self):
        """Test relationships between AdminAction and other models."""
        # Create multiple actions
        action1 = AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.target_account,
            target_user=self.target_user,
            description='First action'
        )
        action2 = AdminAction.objects.create(
            action_type='user_deactivate',
            admin_user=self.admin_user,
            target_user=self.target_user,
            description='Second action'
        )
        
        # Test admin_actions_performed relationship
        performed_actions = self.admin_user.admin_actions_performed.all()
        self.assertIn(action1, performed_actions)
        self.assertIn(action2, performed_actions)
        
        # Test admin_actions_received relationship
        received_actions = self.target_user.admin_actions_received.all()
        self.assertIn(action1, received_actions)
        self.assertIn(action2, received_actions)
        
        # Test admin_actions relationship on BankAccount
        account_actions = self.target_account.admin_actions.all()
        self.assertIn(action1, account_actions)
        self.assertNotIn(action2, account_actions)
    
    def test_model_meta_options(self):
        """Test model meta options."""
        self.assertEqual(AdminAction._meta.db_table, 'admin_actions')
        self.assertEqual(AdminAction._meta.verbose_name, 'Admin Action')
        self.assertEqual(AdminAction._meta.verbose_name_plural, 'Admin Actions')
        self.assertEqual(AdminAction._meta.ordering, ['-timestamp'])
