import { View, type ViewProps } from 'react-native';

export function ThemedView({ className, ...otherProps }: ViewProps) {
  return <View className={`bg-background ${className ?? ''}`} {...otherProps} />;
}