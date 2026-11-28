import { Text, type TextProps } from 'react-native';

export type ThemedTextProps = TextProps & {
  type?: 'default' | 'title' | 'defaultSemiBold' | 'subtitle' | 'link';
};

const variants = {
  default: 'text-base leading-6 text-foreground',
  defaultSemiBold: 'text-base leading-6 font-semibold text-foreground',
  title: 'text-[32px] leading-8 font-bold text-text-strong',
  subtitle: 'text-xl font-bold text-foreground',
  link: 'text-base leading-[30px] text-accent',
} as const;

export function ThemedText({ type = 'default', className, ...rest }: ThemedTextProps) {
  return <Text className={`${variants[type]} ${className ?? ''}`} {...rest} />;
}