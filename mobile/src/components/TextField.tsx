import { Text, TextInput, TextInputProps, View } from 'react-native';

type TextFieldProps = TextInputProps & {
  label: string;
  error?: string;
};

export function TextField({ label, multiline, error, ...props }: TextFieldProps) {
  return (
    <View className="mb-4">
      <Text className={`mb-2 text-sm font-semibold uppercase tracking-wide ${error ? 'text-rose-300' : 'text-slate-400'}`}>
        {label}
      </Text>
      <TextInput
        {...props}
        multiline={multiline}
        placeholderTextColor="#64748b"
        className={`rounded-2xl border bg-white/5 px-4 py-3 text-base text-white ${
          error ? 'border-rose-400' : 'border-white/10'
        } ${
          multiline ? 'min-h-28 align-top' : ''
        }`}
      />
      {error ? <Text className="mt-2 text-sm leading-5 text-rose-200">{error}</Text> : null}
    </View>
  );
}
