import { Pressable, Text, View } from 'react-native';

export type SelectOption = {
  label: string;
  value: string;
};

type SelectFieldProps = {
  label: string;
  value?: string;
  options: SelectOption[];
  error?: string;
  onChange: (value: string) => void;
};

export function SelectField({ label, value, options, error, onChange }: SelectFieldProps) {
  return (
    <View className="mb-4">
      <Text className={`mb-2 text-sm font-semibold uppercase tracking-wide ${error ? 'text-rose-300' : 'text-slate-400'}`}>
        {label}
      </Text>
      <View className="flex-row flex-wrap gap-2">
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => onChange(option.value)}
              className={`rounded-2xl border px-4 py-3 ${
                selected ? 'border-aurora bg-aurora/20' : 'border-white/10 bg-white/5'
              }`}
            >
              <Text className={`font-semibold ${selected ? 'text-white' : 'text-slate-300'}`}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
      {error ? <Text className="mt-2 text-sm leading-5 text-rose-200">{error}</Text> : null}
    </View>
  );
}
