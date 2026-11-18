import type { ComponentPropsWithoutRef } from 'react';
import { Icon } from './graphics';

export function Select({ className = '', children, ...props }: ComponentPropsWithoutRef<'select'>) {
  return (
    <span className={className ? 'select-wrap ' + className : 'select-wrap'}>
      <select {...props}>{children}</select>
      <Icon name="chevron" size={15} />
    </span>
  );
}
