import { Text, TextInput, TextInputProps, View } from 'react-native';

type TextFieldProps = TextInputProps & {
  label: string;
};

export function TextField({ label, multiline, ...props }: TextFieldProps) {
  return (
    <View className="mb-4">
      <Text className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">{label}</Text>
      <TextInput
        {...props}
        multiline={multiline}
        placeholderTextColor="#64748b"
        className={`rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white ${
          multiline ? 'min-h-28 align-top' : ''
        }`}
      />
    </View>
  );
}
