import React, { useState } from 'react';
import { Alert, Image, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { colors } from '../theme/colors';
import { auth } from '../services/auth';
import { useAuth } from '../contexts/AuthContext';

type LoginStep =
  | 'entry'
  | 'login'
  | 'register_email'
  | 'register_code'
  | 'register_password'
  | 'forgot_email'
  | 'forgot_code'
  | 'forgot_password';

export function LoginScreen({ onBack }: { onBack?: () => void } = {}) {
  const { login } = useAuth();
  const [step, setStep] = useState<LoginStep>('entry');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [verifyToken, setVerifyToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [timer, setTimer] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');

  const validatePassword = (value: string): string | null => {
    if (value.length < 8) return 'Password must be at least 8 characters';
    if (/^\d+$/.test(value)) return 'Password cannot be only numbers';
    if (!/[A-Za-z]/.test(value)) return 'Password must include at least one letter';
    if (!/\d/.test(value)) return 'Password must include at least one number';
    return null;
  };

  // Email inputs (especially from iOS keyboard autocomplete/paste) can include invisible
  // unicode whitespace (e.g. NBSP, SIX-PER-EM SPACE, ZWSP) which the backend rejects.
  // Strip all unicode whitespace and zero-width characters before validating/sending.
  const sanitizeEmail = (value: string): string =>
    value.replace(/[\s\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000\uFEFF]/g, '').toLowerCase();

  const isLikelyEmail = (value: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const friendlyApiError = (raw: string): string => {
    const withoutStatus = raw.replace(/^\d{3}\s*/, '').trim();
    try {
      const parsed = JSON.parse(withoutStatus);
      if (typeof parsed?.detail === 'string') return parsed.detail;
    } catch {
      // Fall through to text cleanup.
    }
    return withoutStatus
      .replace(/^\{.*?"detail"\s*:\s*"?/, '')
      .replace(/"?\}?$/, '')
      .trim();
  };

  const showError = (title: string, message: string, actions?: Parameters<typeof Alert.alert>[2]) => {
    setErrorMessage(message);
    Alert.alert(title, message, actions);
  };

  const loginWithPassword = async () => {
    setErrorMessage('');
    const cleanEmail = sanitizeEmail(email);
    if (cleanEmail !== email) setEmail(cleanEmail);
    if (!isLikelyEmail(cleanEmail)) {
      showError('Error', 'Please enter a valid email');
      return;
    }
    const passwordError = validatePassword(password);
    if (passwordError) {
      showError('Error', passwordError);
      return;
    }
    setLoading(true);
    try {
      const result = await auth.loginWithPassword(cleanEmail, password);
      await login(result.access_token, result.user);
      setErrorMessage('');
      onBack?.();
    } catch (err: any) {
      const raw = String(err?.message || '');
      const isNotFound = raw.startsWith('404') || /user not found/i.test(raw);
      const isNoPassword = raw.startsWith('409') || /password not set/i.test(raw);
      const isBadEmail = raw.startsWith('422') || /not a valid email/i.test(raw);
      if (isNotFound) {
        showError(
          'Account not found',
          `No account is registered for ${cleanEmail}. Would you like to sign up for a new account with this email?`,
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Sign Up', onPress: () => { setErrorMessage(''); setPassword(''); setCode(''); setStep('register_email'); } },
          ]
        );
      } else if (isNoPassword) {
        showError(
          'Password not set',
          `This email has not finished registration. Please complete sign up to set a password.`,
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Sign Up', onPress: () => { setErrorMessage(''); setPassword(''); setCode(''); setStep('register_email'); } },
          ]
        );
      } else if (isBadEmail) {
        showError('Invalid email', 'The email address looks invalid. Please retype it.');
      } else {
        showError('Login failed', friendlyApiError(raw) || 'Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const requestRegisterCode = async () => {
    const cleanEmail = sanitizeEmail(email);
    if (cleanEmail !== email) setEmail(cleanEmail);
    if (!isLikelyEmail(cleanEmail)) {
      Alert.alert('Error', 'Please enter a valid email');
      return;
    }
    setLoading(true);
    try {
      const result = await auth.requestCode(cleanEmail);
      setStep('register_code');
      setTimer(Math.ceil(result.expires_in_seconds));
      if (result.delivered) {
        Alert.alert('Code Sent', `Verification code sent to ${cleanEmail}`);
      } else {
        Alert.alert('Code sent', 'Please check your email for the verification code.');
      }
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const verifyRegisterCode = async () => {
    if (code.length !== 6) {
      Alert.alert('Error', 'Code must be 6 digits');
      return;
    }
    setLoading(true);
    try {
      const result = await auth.verifyCode(email, code);
      if (result.next_step === 'verify_password') {
        Alert.alert('Account Exists', 'This email is already signed up. Please use Log In.');
        setStep('login');
        setCode('');
      return;
      }
      setVerifyToken(result.verify_token);
      setStep('register_password');
      setCode('');
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const submitRegisterPassword = async () => {
    const passwordError = validatePassword(password);
    if (passwordError) {
      Alert.alert('Error', passwordError);
      return;
    }
    setLoading(true);
    try {
      const result = await auth.setPassword(verifyToken, password);
      await login(result.access_token, result.user);
      setErrorMessage('');
      onBack?.();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to set password');
    } finally {
      setLoading(false);
    }
  };

  const requestForgotCode = async () => {
    const cleanEmail = sanitizeEmail(email);
    if (cleanEmail !== email) setEmail(cleanEmail);
    if (!isLikelyEmail(cleanEmail)) {
      Alert.alert('Error', 'Please enter a valid email');
      return;
    }
    setLoading(true);
    try {
      const result = await auth.requestForgotCode(cleanEmail);
      setStep('forgot_code');
      setTimer(Math.ceil(result.expires_in_seconds));
      if (result.delivered) {
        Alert.alert('Code Sent', `Reset code sent to ${cleanEmail}`);
      } else {
        Alert.alert('Code sent', 'Please check your email for the reset code.');
      }
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to send reset code');
    } finally {
      setLoading(false);
    }
  };

  const verifyForgotCode = async () => {
    if (code.length !== 6) {
      Alert.alert('Error', 'Code must be 6 digits');
      return;
    }
    setLoading(true);
    try {
      const result = await auth.verifyForgotCode(email, code);
      setVerifyToken(result.verify_token);
      setStep('forgot_password');
      setCode('');
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const submitForgotPassword = async () => {
    const passwordError = validatePassword(password);
    if (passwordError) {
      Alert.alert('Error', passwordError);
      return;
    }
    setLoading(true);
    try {
      const result = await auth.resetPassword(verifyToken, password);
      await login(result.access_token, result.user);
      setErrorMessage('');
      onBack?.();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={s.root}>
      <StatusBar style="dark" />
      {(step !== 'entry' || onBack) && (
        <Pressable
          style={s.backHeader}
          onPress={() => {
            if (step === 'entry' && onBack) {
              onBack();
              return;
            }
            setStep('entry'); setPassword(''); setCode('');
          }}
          hitSlop={12}
        >
          <Text style={s.backHeaderIcon}>‹</Text>
          <Text style={s.backHeaderText}>Home</Text>
        </Pressable>
      )}
      {step === 'entry' && (
        <View style={s.container}>
          <View style={s.brandRow}>
            <Image source={require('../images/Squire Logo.png')} style={s.logo} resizeMode="contain" />
            <Text style={s.brandText}>MYGARDENOS</Text>
          </View>
          <Text style={s.subtitle}>Welcome back to smart lawn care</Text>
          <Pressable style={s.button} onPress={() => setStep('login')}>
            <Text style={s.buttonText}>Log In</Text>
          </Pressable>
          <Pressable style={s.secondaryButton} onPress={() => setStep('register_email')}>
            <Text style={s.secondaryButtonText}>Sign Up</Text>
          </Pressable>
        </View>
      )}

      {step === 'login' && (
        <View style={s.container}>
          <Text style={s.title}>Log In</Text>
          <Text style={s.subtitle}>Sign in with email and password</Text>
          <TextInput
            style={s.input}
            placeholder="Enter your email"
            value={email}
            onChangeText={(v) => setEmail(sanitizeEmail(v))}
            editable={!loading}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TextInput
            style={s.input}
            placeholder="Enter your password"
            value={password}
            onChangeText={setPassword}
            editable={!loading}
            secureTextEntry
          />
          {!!errorMessage && <Text style={s.errorText}>{errorMessage}</Text>}
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={loginWithPassword} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Logging in...' : 'Continue'}</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('forgot_email'); setPassword(''); setCode(''); }}>
            <Text style={s.link}>Forgot Password?</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('entry'); setPassword(''); }}>
            <Text style={s.link}>Back</Text>
          </Pressable>
        </View>
      )}

      {step === 'register_email' && (
        <View style={s.container}>
          <Text style={s.title}>Sign Up</Text>
          <Text style={s.subtitle}>Create account with your email</Text>
          <TextInput
            style={s.input}
            placeholder="Enter your email"
            value={email}
            onChangeText={(v) => setEmail(sanitizeEmail(v))}
            editable={!loading}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={requestRegisterCode} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Sending...' : 'Send Verification Code'}</Text>
          </Pressable>
          <Pressable onPress={() => setStep('entry')}>
            <Text style={s.link}>Back</Text>
          </Pressable>
        </View>
      )}

      {step === 'register_code' && (
        <View style={s.container}>
          <Text style={s.title}>Verification Code</Text>
          <Text style={s.subtitle}>Enter the 6-digit code sent to {email}</Text>
          <TextInput
            style={s.input}
            placeholder="000000"
            value={code}
            onChangeText={setCode}
            editable={!loading}
            keyboardType="number-pad"
            maxLength={6}
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={verifyRegisterCode} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Verifying...' : 'Verify'}</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('register_email'); setCode(''); }}>
            <Text style={s.link}>Back to email</Text>
          </Pressable>
          {timer > 0 && <Text style={s.timer}>Code expires in {timer}s</Text>}
        </View>
      )}

      {step === 'register_password' && (
        <View style={s.container}>
          <Text style={s.title}>Set Password</Text>
          <Text style={s.subtitle}>Use 8+ chars with letters and numbers</Text>
          <TextInput
            style={s.input}
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
            editable={!loading}
            secureTextEntry
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={submitRegisterPassword} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Processing...' : 'Continue'}</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('register_code'); setPassword(''); }}>
            <Text style={s.link}>Back to verification</Text>
          </Pressable>
        </View>
      )}

      {step === 'forgot_email' && (
        <View style={s.container}>
          <Text style={s.title}>Forgot Password</Text>
          <Text style={s.subtitle}>Enter your account email</Text>
          <TextInput
            style={s.input}
            placeholder="Enter your email"
            value={email}
            onChangeText={(v) => setEmail(sanitizeEmail(v))}
            editable={!loading}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={requestForgotCode} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Sending...' : 'Send Reset Code'}</Text>
          </Pressable>
          <Pressable onPress={() => setStep('login')}>
            <Text style={s.link}>Back</Text>
          </Pressable>
        </View>
      )}

      {step === 'forgot_code' && (
        <View style={s.container}>
          <Text style={s.title}>Reset Code</Text>
          <Text style={s.subtitle}>Enter the 6-digit code sent to {email}</Text>
          <TextInput
            style={s.input}
            placeholder="000000"
            value={code}
            onChangeText={setCode}
            editable={!loading}
            keyboardType="number-pad"
            maxLength={6}
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={verifyForgotCode} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Verifying...' : 'Verify'}</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('forgot_email'); setCode(''); }}>
            <Text style={s.link}>Back to email</Text>
          </Pressable>
          {timer > 0 && <Text style={s.timer}>Code expires in {timer}s</Text>}
        </View>
      )}

      {step === 'forgot_password' && (
        <View style={s.container}>
          <Text style={s.title}>New Password</Text>
          <Text style={s.subtitle}>Use 8+ chars with letters and numbers</Text>
          <TextInput
            style={s.input}
            placeholder="New password"
            value={password}
            onChangeText={setPassword}
            editable={!loading}
            secureTextEntry
          />
          <Pressable style={[s.button, loading && s.buttonDisabled]} onPress={submitForgotPassword} disabled={loading}>
            <Text style={s.buttonText}>{loading ? 'Resetting...' : 'Reset Password'}</Text>
          </Pressable>
          <Pressable onPress={() => { setStep('forgot_code'); setPassword(''); }}>
            <Text style={s.link}>Back to verification</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: 80,
  },
  backHeader: {
    position: 'absolute',
    top: 56,
    left: 16,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 8,
    zIndex: 10,
  },
  backHeaderIcon: {
    fontSize: 32,
    color: colors.green,
    lineHeight: 32,
    marginRight: 2,
  },
  backHeaderText: {
    fontSize: 17,
    color: colors.green,
    fontWeight: '600',
  },
  container: {
    paddingHorizontal: 24,
    paddingTop: 40,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginBottom: 18,
  },
  logo: {
    width: 44,
    height: 44,
  },
  brandText: {
    fontSize: 26,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.green,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.green,
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    color: colors.muted,
    marginBottom: 32,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    marginBottom: 20,
    color: '#333',
  },
  errorText: {
    color: colors.darkRed,
    backgroundColor: '#FDECEC',
    borderColor: '#F4B8B8',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    lineHeight: 20,
    marginTop: -6,
    marginBottom: 16,
  },
  button: {
    backgroundColor: colors.green,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  secondaryButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.green,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  secondaryButtonText: {
    color: colors.green,
    fontWeight: '700',
    fontSize: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  link: {
    color: colors.green,
    fontWeight: '600',
    textAlign: 'center',
    fontSize: 14,
  },
  debug: {
    fontSize: 12,
    color: '#FF6B6B',
    backgroundColor: '#FFE0E0',
    padding: 8,
    borderRadius: 6,
    marginBottom: 16,
    fontWeight: '600',
  },
  timer: {
    fontSize: 14,
    color: colors.muted,
    textAlign: 'center',
    marginTop: 12,
  },
});
