import { ActivityIndicator, Pressable, Text } from 'react-native';

type ButtonProps = {
  title: string;
  onPress?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  loading?: boolean;
};

const variants = {
  primary: 'bg-nebula',
  secondary: 'bg-white/10 border border-white/15',
  ghost: 'bg-transparent',
  danger: 'bg-rose-600',
};

export function Button({ title, onPress, variant = 'primary', disabled, loading }: ButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      className={`min-h-12 items-center justify-center rounded-2xl px-5 ${variants[variant]} ${
        disabled || loading ? 'opacity-60' : 'active:opacity-80'
      }`}
    >
      {loading ? (
        <ActivityIndicator color="#ffffff" />
      ) : (
        <Text className="text-base font-bold text-white">{title}</Text>
      )}
    </Pressable>
  );
}
