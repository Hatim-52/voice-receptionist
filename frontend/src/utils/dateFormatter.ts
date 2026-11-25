/**
 * dateFormatter.ts - Formats ISO date strings to 'Thu 26 Nov' format.
 */

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function formatCustomDate(isoDate: string): string {
  if (!isoDate) return '';
  try {
    const parts = isoDate.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return `${DAYS[d.getDay()]} ${day} ${MONTHS[d.getMonth()]}`;
    }
    const d = new Date(isoDate);
    if (!isNaN(d.getTime())) {
      return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
    }
  } catch {
    // Return original string on parse error
  }
  return isoDate;
}
